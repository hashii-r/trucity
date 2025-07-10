import os
import google.generativeai as genai
from dotenv import load_dotenv
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from typing import List
import uvicorn
from marking_ps_gemini import classify_problem_statement

# Load environment variables
load_dotenv()

# Configure Gemini AI
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(model_name="gemini-1.5-flash")

# Initialize FastAPI
app = FastAPI()

# SDG list
sdgs = [
    "No Poverty", "Zero Hunger", "Good Health and Well-being", "Quality Education", "Gender Equality",
    "Clean Water and Sanitation", "Affordable and Clean Energy", "Decent Work and Economic Growth",
    "Industry, Innovation and Infrastructure", "Reduced Inequalities", "Sustainable Cities and Communities",
    "Responsible Consumption and Production", "Climate Action", "Life Below Water", "Life on Land",
    "Peace, Justice and Strong Institutions", "Partnerships for the Goals"
]

# Problem statement evaluation criteria
problem_statement_tips = """
EFFECTIVE PROBLEM STATEMENT ASSESSMENT CRITERIA

1. **Contains Data**: The problem statement includes relevant quantitative or qualitative data supporting the existence of the problem.

2. **References Included**: The statement cites credible sources or references that validate the problem.

3. **Location/Area Clear**: Clearly specifies the geographical location or specific area where the problem exists.

4. **Target Audience Clearly Stated**: Defines the specific group or demographic affected by the problem.

5. **Impact Described**: Explains the consequences or negative impact if the problem remains unaddressed.

6. **GRAMMAR**: The response uses correct grammar, spelling, and punctuation throughout.

7. **DEMONSTRATES UNDERSTANDING**: The answer reflects a clear comprehension of the question or topic, showing insight and awareness.

8. **PRECISE AND TO THE POINT**: The information is concise, avoiding unnecessary details and focusing on the core message.

9. **RELEVANT TO THE IDEA**: The content directly relates to and supports the main idea or purpose being assessed.

10. **INFO IS WELL-STRUCTURED AND EASY TO UNDERSTAND**: The response is logically organized, making it straightforward and accessible for the reader to follow.
"""

# Request models
class SDGRequest(BaseModel):
    sdgs_selected: List[str]

class PSRequest(BaseModel):
    idea: str
    problem_statement: str

# Endpoints
@app.post("/generate_ideas")
def generate_ideas(request: SDGRequest):
    """
    Generate project ideas based on selected SDGs
    """
    selected = request.sdgs_selected
    
    print(f"Selected SDGs: {selected}")

    # Validate SDGs
    for sdg in selected:
        if sdg not in sdgs:
            raise HTTPException(status_code=400, detail=f"Invalid SDG: {sdg}")

    prompt = f"""
    Generate 5 student-friendly, realistic project ideas based on the following Sustainable Development Goals: {', '.join(selected)}.
    Each idea should be:
    - Feasible for students to implement
    - Ethical and socially responsible
    - Involve either technology or social innovation
    - Clearly address one or more of the selected SDGs
    
    Format the ideas as a numbered list.
    Strictly avoid any harmful or dangerous content.
    """
    
    try:
        response = model.generate_content(prompt)
        return {
            "selected_sdgs": selected,
            "project_ideas": response.text.strip(),
            "problem_statement_tips": problem_statement_tips.strip()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating content: {str(e)}")

@app.post("/evaluate_ps")
async def evaluate_problem_statement(request: PSRequest):
    """
    Evaluate a problem statement against a project idea
    """
    try:
        result = classify_problem_statement(request.idea, request.problem_statement)
        
        return {
            "success": result.get("success", False),
            "Problem Statement": request.problem_statement,
            "Idea": request.idea,
            "evaluation": result.get("data"),
            "criteria": problem_statement_tips.strip()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error evaluating problem statement: {str(e)}")



# Run the application
if __name__ == "__main__":
    uvicorn.run("API:app", host="127.0.0.1", port=8000, reload=True)