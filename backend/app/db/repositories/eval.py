from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from app.utils.timezone import beijing_time_now
from .base import BaseRepository


class EvalQuery(BaseModel):
    query_text: str
    relevant_docs: List[Dict[str, Any]]


class EvalDataset(BaseModel):
    id: str
    name: str
    kb_id: str
    queries: List[EvalQuery]
    created_at: datetime = Field(default_factory=beijing_time_now)


class EvalRun(BaseModel):
    id: str
    dataset_id: str
    config: Dict[str, Any]
    results: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    created_at: datetime = Field(default_factory=beijing_time_now)


class EvalRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db)
        self.datasets_collection = self.db.eval_datasets
        self.runs_collection = self.db.eval_runs

    async def create_dataset(self, dataset_data: Dict[str, Any]) -> str:
        if "created_at" not in dataset_data:
            dataset_data["created_at"] = beijing_time_now()

        # Ensure 'id' is mapped to '_id' for MongoDB
        if "id" in dataset_data and "_id" not in dataset_data:
            dataset_data["_id"] = dataset_data.pop("id")

        result = await self.datasets_collection.insert_one(dataset_data)
        return str(result.inserted_id)

    async def get_dataset(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        return await self.datasets_collection.find_one({"_id": dataset_id})

    async def create_run(self, run_data: Dict[str, Any]) -> str:
        if "created_at" not in run_data:
            run_data["created_at"] = beijing_time_now()

        # Ensure 'id' is mapped to '_id' for MongoDB
        if "id" in run_data and "_id" not in run_data:
            run_data["_id"] = run_data.pop("id")

        result = await self.runs_collection.insert_one(run_data)
        return str(result.inserted_id)

    async def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        return await self.runs_collection.find_one({"_id": run_id})
