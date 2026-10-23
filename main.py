from fastapi import FastAPI,HTTPException,Depends,UploadFile,File
from pydantic import BaseModel,ConfigDict
from typing import Optional
from database import engine,Base,SessionLocal
from models import Job
from sqlalchemy.orm import Session
import models
from pathlib import Path
import fitz
from io import BytesIO
from docx import Document
import pytesseract
from PIL import Image

app=FastAPI()
#Module 1
class Job_create(BaseModel):
    job_title:str
    job_description: str
    required_experience: Optional[str]=None
    skills_required: str

Base.metadata.create_all(bind=engine)

def get_db():
    db=SessionLocal()
    try:
        yield db
    finally:
        db.close

@app.get("/")
def home():
    return {"message":"Resume Screening System is runnning.."}

@app.post("/jobs")
def create_job(job: Job_create,db:Session=Depends(get_db)):
    db_job=models.Job(
        job_title=job.job_title,
        job_description=job.job_description,
        required_experience=job.required_experience,
        skills_required=job.skills_required
    )

    db.add(db_job)
    db.commit()
    db.refresh(db_job)

    return {"message":"Job has been created"}


@app.get("/jobs")
def get_job(db:Session=Depends(get_db)):
    jobs=db.query(models.Job).all()
    if not jobs:
        raise HTTPException(
                    status_code=404,
                    detail="Some error has occured"
                )
    return {"message":"Jobs has been fetched",
            "Jobs":jobs}



@app.get("/jobs/{job_id}")
def get_job(job_id:int,db:Session=Depends(get_db)):
    job=db.query(models.Job).filter(
        models.Job.job_id==job_id
    ).first()
    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Match not found for your job"
        )
    return {"message":"Job has been fectched",
            "Job":job}
 
class Job_update(BaseModel):
    job_title:Optional[str]=None
    job_description:Optional[str]=None
    required_experience:Optional[str]=None
    skills_required:Optional[str]=None

@app.patch("/jobs/{job_id}")
def update_job(job_id:int,job:Job_update,db:Session=Depends(get_db)):
    db_job=db.query(models.Job).filter(
        models.Job.job_id==job_id
    ).first()

    if db_job is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found which you want to update"
        )
    updated_data=job.model_dump(exclude_unset=True)

    if not updated_data:                # check if the updated_data is empty or not
        raise HTTPException(
            status_code=400,
            detail="No data provided for update"
        )

    for key ,value in updated_data.items():
        setattr(db_job,key,value)

    db.commit()
    db.refresh(db_job)

    return {"message":"Job has been updated",
            "Job":db_job}

@app.delete("/jobs/{job_id}")
def delete_job(job_id:int, db:Session=Depends(get_db)):
    db_job=db.query(models.Job).filter(
        models.Job.job_id==job_id
    ).first()

    if db_job is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found which you want to delete"
        )
    db.delete(db_job)
    db.commit()
    return {"message":"Job has been deleted"}

#Module 2

class Resume_upload(BaseModel):
    filename:str
    content_type:Optional[str]=None
    file_size:int
    extracted_text:Optional[str]=None

    model_config=ConfigDict(from_attributes=True)

MAX_FILE_SIZE=5*1024*1024
Allowed_Extensions={".pdf",".docx"}   #set of allowed extensions

@app.post("/resumes/upload")
async def upload_resume(file: UploadFile=File(...),db:Session=Depends(get_db)):
    #check if the file is a PDF or DOCX
    extension=Path(file.filename or "").suffix.lower()

    if extension not in Allowed_Extensions:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type"
        )

    #check if the file size is less than 5MB
    file_contents=await file.read()

    if not file_contents:
        raise HTTPException(
            status_code=400,
            detail="File is empty"
        )

    if len(file_contents)>MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File size exceeeds the limit of 5MB"    
        )
    if extension==".pdf":
        #for extracting text from pdf
        with fitz.open(stream=file_contents, filetype="pdf") as pdf:
            text="\n".join(page.get_text() for page in pdf)

            #if the text is empty ,  then will perform ocr extraction
            if not text.strip():
                extracted_pages=[]
                for page in pdf:
                    pix=page.get_pixmap(
                        matrix=fitz.Matrix(2,2),
                        alpha=False
                    )
                    image=Image.open(
                        BytesIO(pix.tobytes("png"))
                    )

                    page_text=pytesseract.image_to_string(
                        image,
                        lang="eng"
                    )
                    extracted_pages.append(page_text)

                    text="\n".join(extracted_pages)
                
    else:
        #for extracting text from docx
        document=Document(BytesIO(file_contents))
        text="\n".join(paragraph.text for paragraph in document.paragraphs)

    db_resume=models.Resume_data(
        filename=file.filename,
        content_type=file.content_type,
        file_size=len(file_contents),
        extracted_text=text
    )
    db.add(db_resume)
    db.commit()
    db.refresh(db_resume)

    response=Resume_upload.model_validate(db_resume)
    return{"message":"File has been uploaded successfully",
           "Resume":response}


@app.delete("/resumes/{resume_id}")
def delete_resume(resume_id: int, db: Session = Depends(get_db)):
    resume = db.query(models.Resume_data).filter(
        models.Resume_data.resume_id == resume_id
    ).first()

    if resume is None:
        raise HTTPException(
            status_code=404,
            detail="Resume not found"
        )

    db.delete(resume)
    db.commit()

    return {
        "message": "Resume deleted successfully",
        "resume_id": resume_id
    }
