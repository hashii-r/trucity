import streamlit as st
import requests
import json
from typing import List

# Configure the page
st.set_page_config(
    page_title="SDG Project Idea Generator",
    page_icon="🌍",
    layout="wide"
)

# API Configuration
API_BASE_URL = "http://127.0.0.1:8000"

# SDG list
sdgs = [
    "No Poverty", "Zero Hunger", "Good Health and Well-being", "Quality Education", "Gender Equality",
    "Clean Water and Sanitation", "Affordable and Clean Energy", "Decent Work and Economic Growth",
    "Industry, Innovation and Infrastructure", "Reduced Inequalities", "Sustainable Cities and Communities",
    "Responsible Consumption and Production", "Climate Action", "Life Below Water", "Life on Land",
    "Peace, Justice and Strong Institutions", "Partnerships for the Goals"
]

def call_generate_ideas_api(selected_sdgs: List[str]):
    """Call the FastAPI endpoint to generate ideas"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/generate_ideas",
            json={"sdgs_selected": selected_sdgs},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error calling API: {str(e)}")
        return None

def call_evaluate_ps_api(idea: str, problem_statement: str):
    """Call the FastAPI endpoint to evaluate problem statement"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/evaluate_ps",
            json={"idea": idea, "problem_statement": problem_statement},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error calling API: {str(e)}")
        return None

def parse_ideas_from_text(ideas_text: str):
    """Parse the generated ideas text into a list"""
    lines = ideas_text.strip().split('\n')
    ideas = []
    for line in lines:
        line = line.strip()
        if line and (line[0].isdigit() or line.startswith('•') or line.startswith('-')):
            # Remove numbering and bullet points
            clean_line = line
            for prefix in ['1.', '2.', '3.', '4.', '5.', '•', '-']:
                if clean_line.startswith(prefix):
                    clean_line = clean_line[len(prefix):].strip()
                    break
            if clean_line:
                ideas.append(clean_line)
    return ideas

# Initialize session state
if 'ideas_generated' not in st.session_state:
    st.session_state.ideas_generated = False
if 'generated_ideas' not in st.session_state:
    st.session_state.generated_ideas = []
if 'selected_sdgs' not in st.session_state:
    st.session_state.selected_sdgs = []
if 'problem_statement_tips' not in st.session_state:
    st.session_state.problem_statement_tips = ""

# Main app
st.title("🌍 SDG Project Idea Generator")
st.markdown("Generate sustainable project ideas and evaluate your problem statements!")

# Step 1: SDG Selection
st.header("Step 1: Select SDGs (Maximum 2)")
st.markdown("Choose up to 2 Sustainable Development Goals for your project:")

# Create columns for better layout
col1, col2 = st.columns(2)

with col1:
    selected_sdgs = st.multiselect(
        "Select SDGs:",
        options=sdgs,
        max_selections=2,
        help="You can select maximum 2 SDGs"
    )

with col2:
    if selected_sdgs:
        st.success(f"Selected {len(selected_sdgs)}/2 SDGs")
        for sdg in selected_sdgs:
            st.write(f"✓ {sdg}")

# Generate Ideas Button
if st.button("🚀 Generate Project Ideas", disabled=len(selected_sdgs) == 0):
    if len(selected_sdgs) > 2:
        st.error("Please select maximum 2 SDGs only!")
    else:
        with st.spinner("Generating ideas..."):
            result = call_generate_ideas_api(selected_sdgs)
            if result:
                st.session_state.ideas_generated = True
                st.session_state.selected_sdgs = selected_sdgs
                st.session_state.problem_statement_tips = result.get("problem_statement_tips", "")
                
                # Parse ideas from the response
                ideas_text = result.get("project_ideas", "")
                parsed_ideas = parse_ideas_from_text(ideas_text)
                st.session_state.generated_ideas = parsed_ideas
                
                st.success("Ideas generated successfully!")

# Step 2: Display Generated Ideas
if st.session_state.ideas_generated and st.session_state.generated_ideas:
    st.header("Step 2: Generated Project Ideas")
    st.markdown(f"**Selected SDGs:** {', '.join(st.session_state.selected_sdgs)}")
    
    # Display ideas as radio buttons for selection
    selected_idea = st.radio(
        "Select one idea to develop:",
        options=st.session_state.generated_ideas,
        format_func=lambda x: f"{st.session_state.generated_ideas.index(x) + 1}. {x}"
    )
    
    if selected_idea:
        st.info(f"**Selected Idea:** {selected_idea}")
        
        # Step 3: Problem Statement
        st.header("Step 3: Write Problem Statement")
        
        # Show tips in an expander
        with st.expander("📋 Problem Statement Tips & Criteria"):
            if st.session_state.problem_statement_tips:
                st.markdown(st.session_state.problem_statement_tips)
        
        # Problem statement input
        problem_statement = st.text_area(
            "Write your problem statement:",
            height=150,
            placeholder="Describe the problem your project aims to solve. Include data, references, location, target audience, and impact...",
            help="Refer to the tips above for guidance on writing an effective problem statement"
        )
        
        # Evaluate button
        if st.button("📊 Evaluate Problem Statement", disabled=not problem_statement.strip()):
            with st.spinner("Evaluating your problem statement..."):
                evaluation_result = call_evaluate_ps_api(selected_idea, problem_statement)
                
                if evaluation_result:
                    st.header("📋 Evaluation Results")
                    
                    # Show success status
                    success = evaluation_result.get("success", False)
                    if success:
                        st.success("✅ Problem Statement Evaluation Completed!")
                    else:
                        st.warning("⚠️ Problem Statement Needs Improvement")
                    
                    # Display evaluation details
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("📝 Your Submission")
                        st.write(f"**Idea:** {evaluation_result.get('Idea', 'N/A')}")
                        st.write(f"**Problem Statement:** {evaluation_result.get('Problem Statement', 'N/A')}")
                    
                    with col2:
                        st.subheader("🔍 Evaluation")
                        evaluation_data = evaluation_result.get("evaluation", "No evaluation data available")
                        st.write(evaluation_data)
                    
                    # Show criteria reference
                    st.subheader("📋 Evaluation Criteria Reference")
                    with st.expander("View Criteria Details"):
                        criteria = evaluation_result.get("criteria", "No criteria available")
                        st.markdown(criteria)

# Sidebar with instructions
st.sidebar.header("📚 How to Use")
st.sidebar.markdown("""
1. **Select SDGs**: Choose up to 2 SDGs that interest you
2. **Generate Ideas**: Click to get 5 project ideas
3. **Select Idea**: Choose one idea from the generated list
4. **Write Problem Statement**: Craft a detailed problem statement
5. **Get Evaluation**: See how well your problem statement meets the criteria
""")

st.sidebar.header("🔧 API Status")
try:
    response = requests.get(f"{API_BASE_URL}/docs", timeout=5)
    if response.status_code == 200:
        st.sidebar.success("✅ API Connected")
    else:
        st.sidebar.error("❌ API Not Responding")
except:
    st.sidebar.error("❌ API Connection Failed")
    st.sidebar.markdown("Make sure your FastAPI server is running on http://127.0.0.1:8000")

# Footer
st.markdown("---")
st.markdown("*Built with Streamlit and FastAPI for SDG Project Development*")