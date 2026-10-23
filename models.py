from sqlalchemy import Integer,Column,String,Text
from database import Base
class Job(Base):
    __tablename__="jobs"

    job_id=Column(Integer,primary_key=True,nullable=False)
    job_title=Column(String(100),nullable=False)
    job_description=Column(Text,nullable=False)
    required_experience=Column(String(50),nullable=True)
    skills_required=Column(Text,nullable=False)

class Resume_data(Base):
    __tablename__="resume_data"

    resume_id=Column(Integer,primary_key=True,nullable=False)
    filename=Column(String(255),nullable=False)
    content_type=Column(String(100),nullable=True)
    file_size=Column(Integer,nullable=False)
    extracted_text=Column(Text,nullable=True)