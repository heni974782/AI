from fastapi import FastAPI, Request, File, UploadFile, BackgroundTasks
from fastapi.templating import Jinja2Templates
import shutil
import ocr
import os
import uuid
import json

#initialize our application 
app = FastAPI()

#define the directory/location where the application wil look for the tempale
templates = Jinja2Templates(directory="templates")

#Serving an HTML templates to use the user interface 
@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request}) #precize that index file is the object to return 

#perform the OCR on a image and return the text 
@app.post("/api/v1/extract_text")
async def extract_text(image: UploadFile = File(...)): # we attache an image payload by using the uploadFile data type (... = place holder)
    temp_file = _save_file_to_disk(image, path="temp", save_as="temp") #download the image uploaded to the server 
    text = await ocr.read_image(temp_file) # we pass the file saved in the local machine to the server to perform the OCR 
    return {"filename": image.filename, "text": text} #dictionary as JSON response

# perfom OCR on multiple images (using background tasks)
@app.post("/api/v1/bulk_extract_text")
async def bulk_extract_text(request: Request, bg_task: BackgroundTasks):
    images = await request.form() # get all the images using the request object 

    #create an folder with unique ID (uuid) and the ID will be the task ID also
    folder_name = str(uuid.uuid4()) 
    os.mkdir(folder_name)

    #save images to the created folder
    for image in images.values():
        temp_file = _save_file_to_disk(image, path=folder_name, save_as=image.filename)

    # queue the OCR task by creating a background tasks
    bg_task.add_task(ocr.read_images_from_dir, folder_name, write_to_file=True)
    return {"task_id": folder_name, "num_files": len(images)} # task id and num of images to process as a return 

# get all the text files generated in the created folder 
@app.get("/api/v1/bulk_output/{task_id}")
async def bulk_output(task_id):
    text_map = {}
    for file_ in os.listdir(task_id):
        if file_.endswith("txt"):
            text_map[file_] = open(os.path.join(task_id, file_)).read()
    return {"task_id": task_id, "output": text_map}

# helper funtion : save the image uploaded to the local machine 
def _save_file_to_disk(uploaded_file, path=".", save_as="default"):
    extension = os.path.splitext(uploaded_file.filename)[-1] # takes the params 
    temp_file = os.path.join(path, save_as + extension)
    with open(temp_file, "wb") as buffer:  # open an emplty file with the same name given (save_as)
        shutil.copyfileobj(uploaded_file.file, buffer) # copies the file object ( image uploaded ) to the new file and returns the name of the file 
    return temp_file