import asyncio
from typing import Dict, Any, List
from uuid import UUID

import pymongo
from beanie import PydanticObjectId
from beanie.odm.operators.find.comparison import In
from fastapi import HTTPException, Depends
from src.config.app_config import get_settings
from src.db_vector.weaviate_rag_non_tenant import delete_one_knowledge_user, get_all_chunk_in_file, \
    delete_one_file_knowledge
from src.dtos.schema_in.knowledge import KnowledgeCreate, KnowledgeUpdate
from src.dtos.schema_out.knowledge import KnowledgeOut, KnowledgeListFileOut, FileListChunkOut, FileOut
from src.models.all_models import Knowledge, File, User
from src.utils.app_util import get_key_name_minio, generate_key_knowledge

settings = get_settings()


async def valid_knowledge(id: UUID, user_id: PydanticObjectId) -> Knowledge:
    knowledge = await Knowledge.find_one(Knowledge.knowledge_id == id, Knowledge.owner.id == user_id)
    if not knowledge:
        raise HTTPException(status_code=404, detail="Knowledge not found")
    return knowledge


class KnowledgeService:
    @staticmethod
    async def create_knowledge(owner_id: User, knowledge: KnowledgeCreate) -> KnowledgeOut:
        knowledge_e = await Knowledge.find_one(Knowledge.name == knowledge.name, Knowledge.owner.id == owner_id.id)
        if knowledge_e:
            raise HTTPException(status_code=400, detail="Knowledge name already exists")
        knowledge_in = Knowledge(
            name=knowledge.name,
            description=knowledge.description,
            owner=owner_id
        )
        s = await knowledge_in.insert()
        owner_id.knowledges.append(knowledge_in)
        await owner_id.save()
        return KnowledgeOut(
            knowledge_id=s.knowledge_id,
            name=knowledge_in.name,
            description=knowledge_in.description,
            created_at=knowledge_in.created_at,
            updated_at=knowledge_in.updated_at,
        )

    @staticmethod
    async def get_knowledge_by_id(id: UUID, user_id: PydanticObjectId) -> KnowledgeListFileOut:
        knowledge = await Knowledge.find_one(Knowledge.knowledge_id == id, Knowledge.owner.id == user_id)
        if not knowledge:
            raise HTTPException(status_code=404, detail="Knowledge not found")
        await knowledge.fetch_link(Knowledge.files)
        return KnowledgeListFileOut(
            knowledge=KnowledgeOut(
                knowledge_id=knowledge.knowledge_id,
                name=knowledge.name,
                description=knowledge.description,
                created_at=knowledge.created_at,
                updated_at=knowledge.updated_at,
            ),
            files=[FileOut(
                file_id=f.file_id,
                name=f.name,
                file_type=f.file_type,
                size=f.size,
                page_count=f.page_count,
                url=f.url,
                is_active=f.is_active,
                chunk_count=f.chunk_count,
                time_import=f.time_import,
                created_at=f.created_at,
                updated_at=f.updated_at
            ) for f in knowledge.files]
        )

    @staticmethod
    async def update_knowledge(id: UUID, data: KnowledgeUpdate, user_id: PydanticObjectId) -> KnowledgeOut:
        knowledge = await Knowledge.find_one(Knowledge.knowledge_id == id, Knowledge.owner.id == user_id)
        if not knowledge:
            raise HTTPException(status_code=404, detail="Knowledge not found")
        if knowledge.name == data.name:
            raise HTTPException(status_code=400, detail="Knowledge name already exists")
        knowledge.description = data.description if data.description else knowledge.description
        knowledge.name = data.name if data.name else knowledge.name
        rs = await knowledge.save()
        return KnowledgeOut(**rs.dict())

    @staticmethod
    async def delete_knowledge(id: UUID, user: User):
        knowledge = await Knowledge.find_one(Knowledge.knowledge_id == id, Knowledge.owner.id == user.id)
        if not knowledge:
            raise HTTPException(status_code=404, detail="Knowledge not found")
        await knowledge.delete()
        delete_one_knowledge_user(user.username, generate_key_knowledge(knowledge.knowledge_id))
        new = [k for k in user.knowledges if k.to_ref().id != knowledge.id]
        # item_removed = False
        
        user.knowledges = new
        await user.save()

    @staticmethod
    async def remove_file_to_knowledge(knowledge_id: UUID, file_id: UUID, user: User):
        knowledge = await Knowledge.find_one(Knowledge.knowledge_id == knowledge_id, Knowledge.owner.id == user.id)
        if not knowledge:
            raise HTTPException(status_code=404, detail="Knowledge not found")
        file = await File.find_one(File.file_id == file_id, File.knowledge.id == knowledge.id)
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        new = [f for f in knowledge.files if f.to_ref().id != file.id]
        knowledge.files = new
        await knowledge.save()
        await file.delete()
        delete_one_file_knowledge(user.username, generate_key_knowledge(knowledge.knowledge_id),
                                  get_key_name_minio(file.url))

    @staticmethod
    async def remove_files_from_knowledge(knowledge_id: UUID, file_ids: List[UUID], user: User):
        knowledge = await Knowledge.find_one(Knowledge.knowledge_id == knowledge_id, Knowledge.owner.id == user.id)
        if not knowledge:
            raise HTTPException(status_code=404, detail="Knowledge not found")

        async def remove_file(file_id: UUID):
            file = await File.find_one(File.file_id == file_id, File.knowledge.id == knowledge.id)
            if not file:
                return None
            await file.delete()
            delete_one_file_knowledge(user.username, generate_key_knowledge(knowledge.knowledge_id),
                                      get_key_name_minio(file.url))
            return file.id

        removed_file_ids = await asyncio.gather(*[remove_file(file_id) for file_id in file_ids])
        removed_file_ids = [id for id in removed_file_ids if id is not None]

        knowledge.files = [f for f in knowledge.files if f.to_ref().id not in removed_file_ids]
        await knowledge.save()

        if not removed_file_ids:
            raise HTTPException(status_code=404, detail="No files found to delete")

    @staticmethod
    async def toggle_file_status(file_id: UUID, knowledge_id: UUID, user_id: PydanticObjectId) -> FileOut:
        knowledge = await Knowledge.find_one(Knowledge.knowledge_id == knowledge_id, Knowledge.owner.id == user_id)
        if not knowledge:
            raise HTTPException(status_code=404, detail="Knowledge not found")
        file = await File.find_one(File.file_id == file_id, File.knowledge.id == knowledge.id)
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        file.is_active = not file.is_active
        file_i = await file.save()
        return FileOut(**file_i.dict())

    @staticmethod
    async def get_chunks_from_file(file_id: UUID, knowledge_id: UUID, user: User) -> FileListChunkOut:
        knowledge = await Knowledge.find_one(Knowledge.knowledge_id == knowledge_id, Knowledge.owner.id == user.id)
        if not knowledge:
            raise HTTPException(status_code=404, detail="Knowledge not found")
        file = await File.find_one(File.file_id == file_id, File.knowledge.id == knowledge.id)
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        rs = get_all_chunk_in_file(user.username, generate_key_knowledge(knowledge.knowledge_id),
                                   get_key_name_minio(file.url))

        return FileListChunkOut(
            file=FileOut(
                file_id=file.file_id,
                name=file.name,
                file_type=file.file_type,
                size=file.size,
                page_count=file.page_count,
                url=file.url,
                is_active=file.is_active,
                chunk_count=file.chunk_count,
                time_import=file.time_import,
                created_at=file.created_at,
                updated_at=file.updated_at
            ),
            chunks=rs
        )

    @staticmethod
    async def get_knowledges_by_ids(knowledge_ids: list[UUID]) -> list[str]:
        knowledges = await Knowledge.find(In(Knowledge.knowledge_id, knowledge_ids)).to_list()
        knowledge_names = [generate_key_knowledge(k.knowledge_id) for k in knowledges]
        return knowledge_names
