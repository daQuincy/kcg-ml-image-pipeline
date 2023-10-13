from fastapi import Request, HTTPException, APIRouter, Response, Query
from datetime import datetime
from utility.minio import cmd
from utility.path import separate_bucket_and_file_path


router = APIRouter()


@router.get("/image/random")
def get_random_image(request: Request, dataset: str = Query(...), size: int = Query(...)):  
    # Use Query to get the dataset and size from query parameters

    # Use $sample to get 'size' random documents
    documents = request.app.completed_jobs_collection.aggregate([
        {"$match": {"task_input_dict.dataset": dataset}},
        {"$sample": {"size": size}}
    ])

    # Convert cursor type to list
    documents = list(documents)
    if len(documents) < size:
        raise HTTPException(status_code=404, detail=f"Not enough distinct images available for requested size of {size}")

    # Verify that the images are distinct
    image_ids = [doc["_id"] for doc in documents]
    if len(image_ids) != len(set(image_ids)):
        raise HTTPException(status_code=400, detail="Randomly selected duplicate images. Try again.")

    for doc in documents:
        doc.pop('_id', None)  # remove the auto generated field
    
    # Return the images as a list in the response
    return {"images": documents}


@router.get("/image/data-by-filepath")
def get_image_data_by_filepath(request: Request, file_path: str = None):

    bucket_name, file_path = separate_bucket_and_file_path(file_path)

    image_data = cmd.get_file_from_minio(request.app.minio_client, bucket_name, file_path)

    # Load data into memory
    content = image_data.read()

    response = Response(content=content, media_type="image/jpeg")

    return response

@router.get("/image/list-metadata")
def get_images_metadata(
    request: Request,
    dataset: str = None,
    limit: int = 20,
    offset: int = 0,
    start_date: str = None,
    end_date: str = None
):
    
    print(f"start_date: {start_date}") 

    # Construct the initial query
    query = {
        '$or': [
            {'task_type': 'image_generation_task'},
            {'task_type': 'inpainting_generation_task'}
        ],
        'task_input_dict.dataset': dataset
    }

    # Update the query based on provided start_date and end_date
    if start_date and end_date:
        query['task_creation_time'] = {'$gte': start_date, '$lte': end_date}
    elif start_date:
        query['task_creation_time'] = {'$gte': start_date}
    elif end_date:
        query['task_creation_time'] = {'$lte': end_date}

    print(f"query: {query}") 
    jobs = request.app.completed_jobs_collection.find(query).sort('task_creation_time', -1).skip(offset).limit(limit)

    images_metadata = []
    for job in jobs:
        image_meta_data = {
            'dataset': job['task_input_dict']['dataset'],
            'task_type': job['task_type'],
            'image_path': job['task_output_file_dict']['output_file_path'],
            'image_hash': job['task_output_file_dict']['output_file_hash']
        }
        images_metadata.append(image_meta_data)

    return images_metadata

