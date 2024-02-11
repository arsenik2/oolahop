import os
from typing import Optional, List

from dotenv import dotenv_values
from fastapi import FastAPI, Body, HTTPException, status
from fastapi.responses import Response
from pydantic import ConfigDict, BaseModel, Field
from pydantic.functional_validators import BeforeValidator

from typing_extensions import Annotated

from bson import ObjectId
import motor.motor_asyncio
from pymongo import ReturnDocument

# config = dotenv_values(".env")

app = FastAPI(
    title="API for Oolahop",
    summary="CRUD Webservice for Gelataria",
)
client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("MONGODB_URL"))
db = client["oolahop"]
gelataria_collection = db.get_collection("gelataria")

# Represents an ObjectId field in the database.
# It will be represented as a `str` on the model so that it can be serialized to JSON.
PyObjectId = Annotated[str, BeforeValidator(str)]


class GelatariaModel(BaseModel):
    """
    Container for a single gelataria record.
    """

    # The primary key for the StudentModel, stored as a `str` on the instance.
    # This will be aliased to `_id` when sent to MongoDB,
    # but provided as `id` in the API requests and responses.
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    name: str = Field(...)
    logo: str = Field(...)
    facebook: str = Field(...)
    tiktok: str = Field(...)
    instagram: str = Field(...)
    form: str = Field(...)
    coupon: str = Field(...)
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "name": "Test Gelataria",
                "logo": "http://gelataria.com",
                "facebook": "http://facebook.com",
                "tiktok": "http://tiktok.com",
                "instagram": "http://instagram.com",
                "form": "http://form.com",
                "coupon": "http://coupon.com",
            }
        },
    )


class UpdateGelatariaModel(BaseModel):
    """
    A set of optional updates to be made to a document in the database.
    """

    name: Optional[str] = None
    logo: Optional[str] = None
    facebook: Optional[str] = None
    tiktok: Optional[str] = None
    instagram: Optional[str] = None
    form: Optional[str] = None
    coupon: Optional[str] = None
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "name": "Test Gelataria",
                "logo": "http://gelataria.com",
                "facebook": "http://facebook.com",
                "tiktok": "http://tiktok.com",
                "instagram": "http://instagram.com",
                "form": "http://form.com",
                "coupon": "http://coupon.com",
            }
        },
    )


class GelatariaCollection(BaseModel):
    """
    A container holding a list of `GelatariaModel` instances.

    This exists because providing a top-level array in a JSON response can be a [vulnerability](https://haacked.com/archive/2009/06/25/json-hijacking.aspx/)
    """

    gelatarias: List[GelatariaModel]


@app.post(
    "/gelatarias/",
    response_description="Add new gelataria",
    response_model=GelatariaModel,
    status_code=status.HTTP_201_CREATED,
    response_model_by_alias=False,
)
async def create_gelataria(gelataria: GelatariaModel = Body(...)):
    """
    Insert a new gelataria record.

    A unique `id` will be created and provided in the response.
    """
    new_gelataria = await gelataria_collection.insert_one(
        gelataria.model_dump(by_alias=True, exclude=["id"])
    )
    created_gelataria = await gelataria_collection.find_one(
        {"_id": new_gelataria.inserted_id}
    )
    return created_gelataria


@app.get(
    "/gelatarias/",
    response_description="List all gelatarias",
    response_model=GelatariaCollection,
    response_model_by_alias=False,
)
async def list_gelatarias():
    """
    List all of the gelatarias data in the database.

    The response is unpaginated and limited to 1000 results.
    """
    return GelatariaCollection(gelatarias=await gelataria_collection.find().to_list(1000))


@app.get(
    "/gelatarias/{id}",
    response_description="Get a single gelataria",
    response_model=GelatariaModel,
    response_model_by_alias=False,
)
async def show_gelataria(id: str):
    """
    Get the record for a specific student, looked up by `id`.
    """
    if (
            gelataria := await gelataria_collection.find_one({"_id": ObjectId(id)})
    ) is not None:
        return gelataria

    raise HTTPException(status_code=404, detail=f"Student {id} not found")


@app.put(
    "/gelatarias/{id}",
    response_description="Update a gelataria",
    response_model=GelatariaModel,
    response_model_by_alias=False,
)
async def update_gelataria(id: str, gelataria: UpdateGelatariaModel = Body(...)):
    """
    Update individual fields of an existing student record.

    Only the provided fields will be updated.
    Any missing or `null` fields will be ignored.
    """
    gelataria = {
        k: v for k, v in gelataria.model_dump(by_alias=True).items() if v is not None
    }

    if len(gelataria) >= 1:
        update_result = await gelataria_collection.find_one_and_update(
            {"_id": ObjectId(id)},
            {"$set": gelataria},
            return_document=ReturnDocument.AFTER,
        )
        if update_result is not None:
            return update_result
        else:
            raise HTTPException(status_code=404, detail=f"Student {id} not found")

    # The update is empty, but we should still return the matching document:
    if (existing_gelataria := await gelataria_collection.find_one({"_id": id})) is not None:
        return existing_gelataria

    raise HTTPException(status_code=404, detail=f"Student {id} not found")


@app.delete("/gelatarias/{id}", response_description="Delete a gelataria")
async def delete_gelataria(id: str):
    """
    Remove a single student record from the database.
    """
    delete_result = await gelataria_collection.delete_one({"_id": ObjectId(id)})

    if delete_result.deleted_count == 1:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(status_code=404, detail=f"Gelataria {id} not found")
