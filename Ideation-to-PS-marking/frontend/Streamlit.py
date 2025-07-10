import streamlit as st
import os
import google.generativeai as genai
from typing import List
from backend.marking_ps_gemini import classify_problem_statement

# Configure the page
st.set_page_config(
    page_title="SDG Project Idea Generator",
    page_icon="🌍",
    layout="wide"
)

# Configure Gemini AI
@st.cache_resource
def initialize_gemini():
    """Initialize Gemini AI with API key from Streamlit secrets"""
    try:
        # Try to get API key from Streamlit secrets first, then environment variables
        api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            st.error("Please set GEMINI_API_KEY in Streamlit secrets or environment variables")
            st.stop()
        
        genai.configure(api_key=api_key)
        return genai.GenerativeModel(model_name="gemini-1.5-flash")
    except Exception as e:
        st.error(f"Error initializing Gemini AI: {str(e)}")
        st.stop()

model = initialize_gemini()

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

def generate_project_ideas(selected_sdgs: List[str]):
    """Generate project ideas using Gemini AI"""
    prompt = f"""
    Generate 5 student-friendly, realistic project ideas based on the following Sustainable Development Goals: {', '.join(selected_sdgs)}.
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
        return response.text.strip()
    except Exception as e:
        st.error(f"Error generating ideas: {str(e)}")
        return None

def evaluate_problem_statement_local(idea: str, problem_statement: str):
    """Evaluate problem statement using local function"""
    try:
        result = classify_problem_statement(idea, problem_statement)
        return result
    except Exception as e:
        st.error(f"Error evaluating problem statement: {str(e)}")
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
            ideas_text = generate_project_ideas(selected_sdgs)
            if ideas_text:
                st.session_state.ideas_generated = True
                st.session_state.selected_sdgs = selected_sdgs
                
                # Parse ideas from the response
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
            st.markdown(problem_statement_tips)
        
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
                evaluation_result = evaluate_problem_statement_local(selected_idea, problem_statement)
                
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
                        st.write(f"**Idea:** {selected_idea}")
                        st.write(f"**Problem Statement:** {problem_statement}")
                    
                    with col2:
                        st.subheader("🔍 Evaluation")
                        evaluation_data = evaluation_result.get("data", "No evaluation data available")
                        st.write(evaluation_data)
                    
                    # Show criteria reference
                    st.subheader("📋 Evaluation Criteria Reference")
                    with st.expander("View Criteria Details"):
                        st.markdown(problem_statement_tips)

# Sidebar with instructions
st.sidebar.header("📚 How to Use")
st.sidebar.markdown("""
1. **Select SDGs**: Choose up to 2 SDGs that interest you
2. **Generate Ideas**: Click to get 5 project ideas
3. **Select Idea**: Choose one idea from the generated list
4. **Write Problem Statement**: Craft a detailed problem statement
5. **Get Evaluation**: See how well your problem statement meets the criteria
""")

st.sidebar.header("🔧 System Status")
st.sidebar.success("✅ All Systems Operational")

# Footer
st.markdown("---")
st.markdown("*Built with Streamlit for SDG Project Development*")