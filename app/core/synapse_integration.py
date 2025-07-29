"""
Azure Synapse integration utilities for ETL operations.
Handles data export and pipeline integration.
"""
import json
import logging
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from pathlib import Path
import asyncio
import aiofiles
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
import pandas as pd

from app.core.config import settings

logger = logging.getLogger(__name__)


class SynapseDataExporter:
    """Handles data export to Azure Synapse Analytics."""
    
    def __init__(self):
        self.blob_service_client = None
        self.container_name = getattr(settings, 'SYNAPSE_CONTAINER_NAME', 'hospital-analytics')
        self.storage_account_name = getattr(settings, 'AZURE_STORAGE_ACCOUNT_NAME', None)
        
        if self.storage_account_name:
            try:
                credential = DefaultAzureCredential()
                account_url = f"https://{self.storage_account_name}.blob.core.windows.net"
                self.blob_service_client = BlobServiceClient(
                    account_url=account_url,
                    credential=credential
                )
            except Exception as e:
                logger.warning(f"Could not initialize Azure Blob Storage client: {e}")
    
    async def export_to_json(
        self, 
        data: Dict[str, Any], 
        filename: str,
        local_path: Optional[str] = None
    ) -> str:
        """Export data to JSON format."""
        try:
            if local_path is None:
                local_path = f"/tmp/synapse_exports/{filename}"
            
            # Ensure directory exists
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Convert datetime objects to strings for JSON serialization
            json_data = self._serialize_datetime_objects(data)
            
            async with aiofiles.open(local_path, 'w') as f:
                await f.write(json.dumps(json_data, indent=2, default=str))
            
            logger.info(f"Data exported to JSON: {local_path}")
            return local_path
            
        except Exception as e:
            logger.error(f"Error exporting data to JSON: {e}")
            raise
    
    async def export_to_parquet(
        self, 
        data: List[Dict[str, Any]], 
        filename: str,
        local_path: Optional[str] = None
    ) -> str:
        """Export data to Parquet format for better Synapse performance."""
        try:
            if local_path is None:
                local_path = f"/tmp/synapse_exports/{filename}"
            
            # Ensure directory exists
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Convert to DataFrame and export to Parquet
            df = pd.DataFrame(data)
            
            # Handle datetime columns
            for col in df.columns:
                if df[col].dtype == 'object':
                    # Try to convert datetime strings
                    try:
                        df[col] = pd.to_datetime(df[col], errors='ignore')
                    except:
                        pass
            
            df.to_parquet(local_path, index=False)
            
            logger.info(f"Data exported to Parquet: {local_path}")
            return local_path
            
        except Exception as e:
            logger.error(f"Error exporting data to Parquet: {e}")
            raise
    
    async def upload_to_blob_storage(
        self, 
        local_file_path: str, 
        blob_name: str
    ) -> str:
        """Upload file to Azure Blob Storage."""
        try:
            if not self.blob_service_client:
                raise ValueError("Blob Storage client not initialized")
            
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            with open(local_file_path, 'rb') as data:
                blob_client.upload_blob(data, overwrite=True)
            
            blob_url = f"https://{self.storage_account_name}.blob.core.windows.net/{self.container_name}/{blob_name}"
            logger.info(f"File uploaded to blob storage: {blob_url}")
            return blob_url
            
        except Exception as e:
            logger.error(f"Error uploading to blob storage: {e}")
            raise
    
    async def export_and_upload_data(
        self, 
        data: Dict[str, Any], 
        data_type: str,
        export_format: str = "parquet"
    ) -> Dict[str, str]:
        """Export data and upload to Azure Blob Storage."""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            uploaded_files = {}
            
            for table_name, table_data in data.items():
                if not table_data:
                    continue
                
                filename = f"{data_type}_{table_name}_{timestamp}"
                
                if export_format == "json":
                    filename += ".json"
                    local_path = await self.export_to_json(
                        {table_name: table_data}, 
                        filename
                    )
                elif export_format == "parquet":
                    filename += ".parquet"
                    local_path = await self.export_to_parquet(
                        table_data, 
                        filename
                    )
                else:
                    raise ValueError(f"Unsupported export format: {export_format}")
                
                # Upload to blob storage if configured
                if self.blob_service_client:
                    blob_name = f"etl/{data_type}/{filename}"
                    blob_url = await self.upload_to_blob_storage(local_path, blob_name)
                    uploaded_files[table_name] = blob_url
                else:
                    uploaded_files[table_name] = local_path
            
            logger.info(f"Exported and uploaded {len(uploaded_files)} files for {data_type}")
            return uploaded_files
            
        except Exception as e:
            logger.error(f"Error exporting and uploading data: {e}")
            raise
    
    def _serialize_datetime_objects(self, obj: Any) -> Any:
        """Recursively serialize datetime objects to strings."""
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {key: self._serialize_datetime_objects(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_datetime_objects(item) for item in obj]
        else:
            return obj


class SynapsePipelineTrigger:
    """Handles triggering Azure Data Factory pipelines for Synapse integration."""
    
    def __init__(self):
        self.adf_client = None
        self.resource_group_name = getattr(settings, 'AZURE_RESOURCE_GROUP', None)
        self.data_factory_name = getattr(settings, 'AZURE_DATA_FACTORY_NAME', None)
        
        # Initialize ADF client if credentials are available
        if self.resource_group_name and self.data_factory_name:
            try:
                from azure.mgmt.datafactory import DataFactoryManagementClient
                from azure.identity import DefaultAzureCredential
                
                credential = DefaultAzureCredential()
                subscription_id = getattr(settings, 'AZURE_SUBSCRIPTION_ID', None)
                
                if subscription_id:
                    self.adf_client = DataFactoryManagementClient(
                        credential, 
                        subscription_id
                    )
            except ImportError:
                logger.warning("Azure Data Factory SDK not available")
            except Exception as e:
                logger.warning(f"Could not initialize ADF client: {e}")
    
    async def trigger_pipeline(
        self, 
        pipeline_name: str, 
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Trigger an Azure Data Factory pipeline."""
        try:
            if not self.adf_client:
                logger.warning("ADF client not available, simulating pipeline trigger")
                return {
                    "status": "simulated",
                    "pipeline_name": pipeline_name,
                    "parameters": parameters,
                    "run_id": f"mock_run_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                }
            
            # Trigger the pipeline
            run_response = self.adf_client.pipeline_runs.create_run(
                resource_group_name=self.resource_group_name,
                factory_name=self.data_factory_name,
                pipeline_name=pipeline_name,
                parameters=parameters or {}
            )
            
            result = {
                "status": "triggered",
                "pipeline_name": pipeline_name,
                "run_id": run_response.run_id,
                "parameters": parameters
            }
            
            logger.info(f"Pipeline triggered successfully: {pipeline_name} (Run ID: {run_response.run_id})")
            return result
            
        except Exception as e:
            logger.error(f"Error triggering pipeline {pipeline_name}: {e}")
            raise
    
    async def get_pipeline_status(self, run_id: str) -> Dict[str, Any]:
        """Get the status of a pipeline run."""
        try:
            if not self.adf_client:
                return {
                    "run_id": run_id,
                    "status": "simulated",
                    "message": "ADF client not available"
                }
            
            run_status = self.adf_client.pipeline_runs.get(
                resource_group_name=self.resource_group_name,
                factory_name=self.data_factory_name,
                run_id=run_id
            )
            
            result = {
                "run_id": run_id,
                "status": run_status.status,
                "pipeline_name": run_status.pipeline_name,
                "run_start": run_status.run_start.isoformat() if run_status.run_start else None,
                "run_end": run_status.run_end.isoformat() if run_status.run_end else None,
                "message": run_status.message
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting pipeline status for run {run_id}: {e}")
            raise


class ETLOrchestrator:
    """Orchestrates ETL operations for Synapse integration."""
    
    def __init__(self):
        self.data_exporter = SynapseDataExporter()
        self.pipeline_trigger = SynapsePipelineTrigger()
    
    async def run_full_etl(
        self, 
        analytics_service,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Run full ETL process for all data types."""
        try:
            etl_results = {
                "start_time": datetime.utcnow().isoformat(),
                "data_exports": {},
                "pipeline_runs": {},
                "status": "running"
            }
            
            # Export all data types
            data_types = ["appointments", "resources", "doctors"]
            
            for data_type in data_types:
                try:
                    # Get data from analytics service
                    data = analytics_service.export_data_for_synapse(
                        data_type, start_date, end_date
                    )
                    
                    # Export and upload data
                    uploaded_files = await self.data_exporter.export_and_upload_data(
                        data, data_type, "parquet"
                    )
                    
                    etl_results["data_exports"][data_type] = uploaded_files
                    
                    # Trigger corresponding pipeline
                    pipeline_name = f"hospital_{data_type}_etl_pipeline"
                    pipeline_params = {
                        "start_date": start_date.isoformat() if start_date else None,
                        "end_date": end_date.isoformat() if end_date else None,
                        "data_files": uploaded_files
                    }
                    
                    pipeline_result = await self.pipeline_trigger.trigger_pipeline(
                        pipeline_name, pipeline_params
                    )
                    
                    etl_results["pipeline_runs"][data_type] = pipeline_result
                    
                except Exception as e:
                    logger.error(f"Error processing {data_type} ETL: {e}")
                    etl_results["pipeline_runs"][data_type] = {
                        "status": "failed",
                        "error": str(e)
                    }
            
            etl_results["end_time"] = datetime.utcnow().isoformat()
            etl_results["status"] = "completed"
            
            logger.info("Full ETL process completed")
            return etl_results
            
        except Exception as e:
            logger.error(f"Error running full ETL: {e}")
            etl_results["status"] = "failed"
            etl_results["error"] = str(e)
            etl_results["end_time"] = datetime.utcnow().isoformat()
            return etl_results
    
    async def run_incremental_etl(
        self, 
        analytics_service,
        data_type: str,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Run incremental ETL for specific data type and date range."""
        try:
            etl_result = {
                "start_time": datetime.utcnow().isoformat(),
                "data_type": data_type,
                "date_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "status": "running"
            }
            
            # Get incremental data
            data = analytics_service.export_data_for_synapse(
                data_type, start_date, end_date
            )
            
            # Export and upload data
            uploaded_files = await self.data_exporter.export_and_upload_data(
                data, f"{data_type}_incremental", "parquet"
            )
            
            etl_result["data_exports"] = uploaded_files
            
            # Trigger incremental pipeline
            pipeline_name = f"hospital_{data_type}_incremental_etl_pipeline"
            pipeline_params = {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "data_files": uploaded_files,
                "mode": "incremental"
            }
            
            pipeline_result = await self.pipeline_trigger.trigger_pipeline(
                pipeline_name, pipeline_params
            )
            
            etl_result["pipeline_run"] = pipeline_result
            etl_result["end_time"] = datetime.utcnow().isoformat()
            etl_result["status"] = "completed"
            
            logger.info(f"Incremental ETL completed for {data_type}")
            return etl_result
            
        except Exception as e:
            logger.error(f"Error running incremental ETL for {data_type}: {e}")
            etl_result["status"] = "failed"
            etl_result["error"] = str(e)
            etl_result["end_time"] = datetime.utcnow().isoformat()
            return etl_result