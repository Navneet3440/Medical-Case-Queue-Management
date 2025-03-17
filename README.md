# AI Medical Case Queue Management System

This system implements an intelligent queue management solution for medical cases, optimizing patient-doctor assignments while ensuring SLA compliance and adapting to real-time changes.

## Features

- Dynamic case prioritization based on urgency, wait time, and SLA deadlines
- Intelligent doctor matching considering specialties, workload, and availability
- Real-time queue updates and adaptable scheduling
- RESTful API interface for system integration
- SLA compliance monitoring and enforcement
- Comprehensive doctor and patient profile management

## Installation

1. Create a virtual environment:
```bash
conda create -n medical-queue python=3.9
conda activate medical-queue
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

Start the FastAPI server:
```bash
uvicorn api:app --reload
```

The API will be available at `http://localhost:8000`

