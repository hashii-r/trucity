import streamlit as st
import os
import json
from typing import List, Optional
from dotenv import load_dotenv
from tavily import TavilyClient
import google.generativeai as genai

# === Load API keys ===
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# Fallback for direct API key (from second app)
if not GEMINI_API_KEY:
    GEMINI_API_KEY = "AIzaSyCtlOq3aAPIdabox2Z1ENUiYLKn6Y_5KwE"  # Replace with your actual API key

# === Configure APIs ===
@st.cache_resource
def setup_apis():
    """Setup and cache API clients"""
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel(model_name="gemini-1.5-flash")
    tavily_client = None
    if TAVILY_API_KEY:
        tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
    return gemini_model, tavily_client

# === JSON Path ===
json_file = "problem.json"

# === SDG List ===
SDG_LIST = [
    "No Poverty",
    "Zero Hunger", 
    "Good Health and Well-being",
    "Quality Education",
    "Gender Equality",
    "Clean Water and Sanitation",
    "Affordable and Clean Energy",
    "Decent Work and Economic Growth",
    "Industry, Innovation and Infrastructure",
    "Reduced Inequalities",
    "Sustainable Cities and Communities",
    "Responsible Consumption and Production",
    "Climate Action",
    "Life Below Water",
    "Life on Land",
    "Peace, Justice and Strong Institutions",
    "Partnerships for the Goals"
]

# === Helper Functions ===
@st.cache_data
def load_problems():
    """Load problems from JSON file"""
    if not os.path.exists(json_file):
        return []
    try:
        with open(json_file, "r") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading problems: {e}")
        return []

def find_matching_problem(problems: List[dict], sdgs: List[str], problem_text: str, idea_text: str):
    """Find a problem that matches the given criteria"""
    for problem_data in problems:
        # Check if any of the requested SDGs match
        problem_sdgs = problem_data.get("sdgs", [])
        if any(sdg in problem_sdgs for sdg in sdgs):
            # If problem and idea are provided, try to match them
            if problem_text and idea_text:
                if (problem_text.lower() in problem_data["problem"].lower() and 
                    idea_text in problem_data.get("ideas", [])):
                    return problem_data
            # If only problem is provided
            elif problem_text and problem_text.lower() in problem_data["problem"].lower():
                return problem_data
    return None

def generate_student_questions(problem: str, idea: str, market_research: str):
    """Generate student-friendly questions based on problem, idea, and market research"""
    
    gemini_model, _ = setup_apis()
    
    prompt = f"""
You are helping a student prepare for a presentation or conference.

Given the problem, solution idea, and market research data below, generate 5 short, direct questions that the student could ask the audience or panel during their presentation.

Each question should:
- Start directly with question words (What, How, Why, When, Where, Which, Who)
- Be one sentence only
- Be concise and clear (avoid long introductory phrases)
- Focus on getting actionable feedback from the audience
- Relate to the problem, solution, and market context provided

### Problem Statement:
{problem}

### Proposed Solution/Idea:
{idea}

### Market Research Findings:
{market_research}

Generate 5 direct questions that start with question words. Avoid phrases like "Given that...", "Considering...", "Since...", "In light of...". 

Only return a numbered list of 5 questions from the **student to the audience**.
"""
    
    try:
        response = gemini_model.generate_content(prompt)
        raw_questions = response.text.strip()
        
        # Parse questions
        questions = []
        for line in raw_questions.split("\n"):
            if line.strip() and line[0].isdigit():
                question_text = line.split(".", 1)[1].strip()
                questions.append(question_text)
        
        return questions
        
    except Exception as e:
        st.error(f"Error generating questions: {str(e)}")
        return []

def generate_sdg_questions(selected_sdgs: List[str], context: Optional[str] = None):
    """Generate questions based on selected SDGs"""
    
    gemini_model, _ = setup_apis()
    
    if not selected_sdgs:
        return []
    
    sdg_list = "\n".join([f"- {sdg}" for sdg in selected_sdgs])
    
    context_section = ""
    if context:
        context_section = f"""
### Additional Context:
{context}
"""
    
    prompt = f"""
You are helping a student prepare for a presentation focused on the UN Sustainable Development Goals (SDGs).

Based on the selected SDGs below, generate 5 short, clear, and audience-facing questions that the student could ask the audience or panel during their presentation.

Each question should be:
- One sentence only
- In a curious, engaging, and student-appropriate tone
- Directly related to the selected SDGs
- Aimed at opening discussion about sustainable development challenges and solutions

### Selected SDGs:
{sdg_list}
{context_section}
Only return a numbered list of 5 questions from the **student to the audience** about these SDGs.
"""
    
    try:
        response = gemini_model.generate_content(prompt)
        raw_questions = response.text.strip()
        
        # Parse questions
        questions = []
        for line in raw_questions.split("\n"):
            if line.strip() and line[0].isdigit():
                question_text = line.split(".", 1)[1].strip()
                questions.append(question_text)
        
        return questions
        
    except Exception as e:
        st.error(f"Error generating SDG questions: {str(e)}")
        return []

def generate_research(sdgs: List[str], problem: str, idea: str, target_market: str, research_question: str):
    """Generate market research insights"""
    
    # Setup APIs
    gemini_model, tavily_client = setup_apis()
    
    # Determine how to get problem and idea data
    selected_problem_data = None
    
    if problem and idea:
        # Use provided problem and idea (most common case)
        selected_problem_data = {
            "problem": problem,
            "ideas": [idea],
            "sdgs": sdgs
        }
    else:
        # Try to find matching problem from JSON file (if it exists)
        problems = load_problems()
        if problems:
            selected_problem_data = find_matching_problem(problems, sdgs, problem, idea)
        
        if not selected_problem_data:
            st.error("Either provide both 'problem' and 'idea', or ensure problem_ideas.json exists with matching data")
            return None
    
    selected_problem = selected_problem_data["problem"]
    selected_idea = idea if idea else selected_problem_data.get("ideas", [""])[0]
    
    try:
        # Tavily Search (only if API key is available)
        web_summary = "No web search available - Tavily API key not configured."
        source_urls = []
        
        if tavily_client:
            search_query = f"{research_question} for {target_market} SDG {' '.join(sdgs)}"
            
            with st.spinner("Searching the web for latest insights..."):
                try:
                    tavily_result = tavily_client.search(
                        query=search_query,
                        include_answer=True,
                        include_sources=True,
                        search_depth="advanced"
                    )
                    web_summary = tavily_result.get("answer", "No summary available.")
                    sources = tavily_result.get("sources", [])
                    source_urls = [src.get('url', '') for src in sources if src.get('url')]
                except Exception as e:
                    st.warning(f"Web search error: {e}")
                    web_summary = "No summary available due to search API error."
                    source_urls = []

        # Gemini Prompt
        prompt = f"""
You are a market research assistant helping with Sustainable Development Goals (SDGs).
Use the below web information to give the latest insights:

Web Research Summary:
{web_summary}

Web Sources:
{', '.join(source_urls)}

Now analyze the following:

Target Market: {target_market}
Research Question: {research_question}
Problem: {selected_problem}
Idea: {selected_idea}
SDGs: {', '.join(sdgs)}

Please provide:
1. Detailed market research insights based on this target market.
2. A separate list of major competitors in this market.

Format your response clearly with these two sections.
"""

        with st.spinner("Generating AI insights..."):
            try:
                gemini_response = gemini_model.generate_content(prompt)
                response_text = gemini_response.text.strip()

                # Split response into market research and competitors
                if "1." in response_text and "2." in response_text:
                    parts = response_text.split("2.")
                    market_research = parts[0].replace("1.", "").strip()
                    competitors = parts[1].strip()
                else:
                    # If the response doesn't follow the expected format, try to split differently
                    lines = response_text.split('\n')
                    market_research_lines = []
                    competitor_lines = []
                    current_section = "market"
                    
                    for line in lines:
                        if "competitor" in line.lower() or "competition" in line.lower():
                            current_section = "competitor"
                        
                        if current_section == "market":
                            market_research_lines.append(line)
                        else:
                            competitor_lines.append(line)
                    
                    market_research = '\n'.join(market_research_lines).strip()
                    competitors = '\n'.join(competitor_lines).strip()
                    
                    if not competitors:
                        competitors = "Competitor information not clearly separated in the response."

            except Exception as e:
                st.error(f"AI model error: {e}")
                market_research = "Unable to generate market research due to AI model error."
                competitors = "Unable to generate competitor insights due to AI model error."

        # Return results
        return {
            "web_summary": web_summary,
            "market_research": market_research,
            "competitor_insights": competitors,
            "web_sources": source_urls,
            "problem": selected_problem,
            "idea": selected_idea,
            "sdgs": sdgs,
            "target_market": target_market,
            "research_question": research_question
        }

    except Exception as e:
        st.error(f"Internal error: {str(e)}")
        return None

# === Rubric Prompt for Market Fit Evaluator ===
RUBRIC_PROMPT = """Student Response Evaluation Template**

You are a supportive business mentor evaluating a young entrepreneur's market analysis. A student (aged 14-15) has submitted a response about their business idea. Please evaluate their work using this 10-point rubric, providing encouraging yet constructive feedback.

**Evaluation Criteria (1-10 scale, where 1 = needs significant improvement, 10 = excellent):**

1. **Target Audience Clarity** - Do they clearly identify who their customers are and what those customers need?
2. **Problem-Solution Connection** - Do they explain how their idea solves a real problem for their target customers?
3. **Market Research Evidence** - Do they include any supporting data, research, or validation (surveys, interviews, observations)?
4. **Unique Value Proposition** - Do they explain what makes their idea different or better than existing solutions?
5. **Market Entry Strategy** - Do they outline realistic first steps for launching their idea (MVP, pilot testing, initial customers)?
6. **Communication Quality** - Is their writing clear with proper grammar, spelling, and punctuation?
7. **Business Understanding** - Do they demonstrate solid comprehension of basic business concepts?
8. **Focus and Conciseness** - Do they stay on topic and communicate efficiently without unnecessary details?
9. **Relevance and Consistency** - Does all content directly relate to supporting their business idea?
10. **Organization and Clarity** - Is their response well-structured and easy to follow?

**Feedback Guidelines:**
- Always address the student directly using "you" and "your"
- Use encouraging, constructive language appropriate for teenagers
- Provide specific examples from their response
- Offer concrete suggestions for improvement
- Acknowledge strengths before addressing areas for growth
- Format feedback as numbered points (1-10) with scores and detailed comments

**Special Scenarios to Handle:**

**When students submit the evaluation template/rubric itself:**
- Respond: "I can see you've shared the evaluation rubric with me! However, I need to see YOUR actual business idea to evaluate it. Please tell me about your business concept - what product or service do you want to create, why is it needed, who would buy it, and how would you launch it? Once you share your business idea, I'll use this rubric to give you helpful feedback!"

**Blank/No Response:**
- "I'd love to help evaluate your business idea! Please share your thoughts about: What business idea do you have? What problem does it solve? Who would be your customers? What makes your idea unique? How would you get started?"

**Very Brief Response (1-3 sentences):**
- Acknowledge their start positively
- Ask specific follow-up questions to help them expand
- Guide them to address missing rubric areas

**Off-Topic Content (personal stories, unrelated topics):**
- Find any business-relevant connections if possible
- Gently redirect: "I can see you're passionate about [topic]! Now let's focus on turning this into a business opportunity. How could you create a product or service around this interest?"

**Inappropriate/Harmful Content:**
- Professionally redirect: "Let's focus on positive business ideas that can help people and create value in the market. What's a problem you've noticed that you could solve with a business?"

**Copy-Pasted Content from Internet:**
- "I can see you've done some research, which is great! Now I'd like to hear YOUR original thoughts and ideas. What's your unique perspective on this business opportunity?"

**Multiple Unrelated Ideas:**
- "You have so many creative ideas! For this evaluation, let's focus on developing ONE business concept thoroughly. Which idea excites you the most? Let's dive deep into that one."

**Purely Technical/Product Descriptions:**
- "This technical concept sounds interesting! Now help me understand the business side - who would pay for this? What problem does it solve for them? How would you make money?"

**Unrealistic/Impossible Ideas:**
- Encourage creativity while gently guiding toward feasibility
- "I love your innovative thinking! Let's explore how we could make this idea more practical to launch. What would be a simpler first version?"

**Poor Market Fit/No Clear Market:**
- Validate creativity first
- Guide toward: "Who specifically would pay for this? What pain point does it solve? How could we test if people actually want this?"

**Ideas That Already Exist:**
- "This shows you understand a real market need! What could make your version different or better? How could you add a unique twist or serve an underserved segment?"

**Vague/Abstract Ideas:**
- Ask for specifics: "This concept has potential! Can you give me concrete examples? What exactly would customers buy? How much would it cost?"

**Student Asks for Help/Doesn't Know What to Write:**
- "That's totally normal! Start by thinking about problems you or your friends face daily. What annoys you? What takes too long? What costs too much? Pick one problem and think about how you could solve it with a business."

**Homework/Assignment Instructions Posted:**
- "I can see the assignment instructions! What I need now is YOUR response to these questions. Tell me about your business idea in your own words."

**Random Text/Gibberish/Testing:**
- "I can see you're testing the system! I'm here to help evaluate your business ideas. When you're ready to share a business concept, I'll give you detailed feedback using the 10-point rubric."

**Questions About the Assignment:**
- Answer briefly, then redirect: "Great question! [Brief answer]. Now let's focus on your business idea - what concept would you like me to evaluate?"

**Personal Information/Life Stories:**
- "Thanks for sharing! I can see you have interesting experiences. How could you turn any of these experiences into a business opportunity? What problems have you noticed that you could solve?"

**Jokes/Silly Responses:**
- Respond with gentle humor, then redirect: "I appreciate the creativity! Now let's channel that creative energy into a business idea. What's something you're genuinely interested in that could become a business?"

**Response Structure:**
Always begin with an encouraging statement, then provide numbered feedback (1-10), and end with motivational guidance for next steps. If the response doesn't warrant full rubric evaluation, explain why and guide them toward providing evaluable content.

Remember: These students are learning entrepreneurship basics. Your goal is to build their confidence while developing their business thinking and communication skills. Every interaction should feel supportive and help them grow as young entrepreneurs.
"""

def evaluate_student_response(student_input: str):
    """Evaluate student response using the rubric"""
    gemini_model, _ = setup_apis()
    
    full_prompt = RUBRIC_PROMPT + "\n\nStudent Response:\n" + student_input.strip()
    
    try:
        response = gemini_model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return f"Error generating feedback: {e}"

# === Streamlit App ===
def main():
    st.set_page_config(
        page_title="SDG Market Research & Evaluation Tool",
        page_icon="🌍",
        layout="wide"
    )
    
    st.title("🌍 SDG Market Research & Evaluation Tool")
    st.markdown("Comprehensive platform for market research, question generation, and business idea evaluation for Sustainable Development Goals")
    
    # Check API keys
    if not GEMINI_API_KEY:
        st.error("⚠️ Please set your GEMINI_API_KEY in your .env file or update the code with your API key")
        st.stop()
    
    # Sidebar for data exploration
    with st.sidebar:
        st.header("📊 Data Explorer")
        
        # Load problems data
        problems = load_problems()
        
        if problems:
            st.success(f"✅ Loaded {len(problems)} problems from JSON")
            
            # Show available SDGs
            all_sdgs = sorted({sdg for p in problems for sdg in p.get("sdgs", [])})
            st.subheader("Available SDGs:")
            for sdg in all_sdgs:
                st.write(f"• {sdg}")
            
            # SDG filter
            selected_sdg_filter = st.selectbox("Filter problems by SDG:", ["All"] + all_sdgs)
            
            if selected_sdg_filter != "All":
                filtered_problems = [p for p in problems if selected_sdg_filter in p.get("sdgs", [])]
                st.subheader(f"Problems for {selected_sdg_filter}:")
                for problem in filtered_problems:
                    with st.expander(problem["problem"][:50] + "..."):
                        st.write("**Problem:**", problem["problem"])
                        st.write("**Ideas:**")
                        for idea in problem.get("ideas", []):
                            st.write(f"• {idea}")
                        st.write("**SDGs:**", ", ".join(problem.get("sdgs", [])))
        else:
            st.info("No problem.json file found. You can still use the market research and evaluation tools.")
        
        # API Status
        st.header("🔌 API Status")
        st.write("✅ Gemini AI: Connected")
        if TAVILY_API_KEY:
            st.write("✅ Tavily Search: Connected")
        else:
            st.write("⚠️ Tavily Search: Not configured (optional)")
    
    # Main tabs
    tab1, tab2, tab3 = st.tabs(["🔍 Market Research", "❓ Question Generator", "📊 Market Fit Evaluator"])
    
    with tab1:
        st.header("🔍 Market Research Parameters")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # SDG selection with smart validation
            if problems:
                all_sdgs = sorted({sdg for p in problems for sdg in p.get("sdgs", [])})
                
                # Initialize session state for SDG selection
                if 'selected_sdgs_research' not in st.session_state:
                    st.session_state.selected_sdgs_research = []
                
                # Custom SDG selector with checkboxes
                st.subheader("Select SDGs (Maximum 2):")
                st.write("🎯 Choose up to 2 SDGs for focused research")
                
                selected_sdgs = []
                for sdg in all_sdgs:
                    # Disable checkbox if already 2 selected and this one isn't selected
                    disabled = len(st.session_state.selected_sdgs_research) >= 2 and sdg not in st.session_state.selected_sdgs_research
                    
                    is_checked = st.checkbox(
                        sdg,
                        value=sdg in st.session_state.selected_sdgs_research,
                        disabled=disabled,
                        key=f"sdg_research_{sdg}"
                    )
                    
                    if is_checked:
                        selected_sdgs.append(sdg)
                
                # Update session state
                st.session_state.selected_sdgs_research = selected_sdgs
                
                # Show selection count
                if len(selected_sdgs) > 0:
                    st.success(f"✅ Selected {len(selected_sdgs)}/2 SDGs: {', '.join(selected_sdgs)}")
                else:
                    st.info("Please select at least 1 SDG")
                
            else:
                # Fallback to multiselect for manual entry
                st.subheader("Select SDGs (Maximum 2):")
                
                # Initialize session state
                if 'selected_sdgs_research' not in st.session_state:
                    st.session_state.selected_sdgs_research = []
                
                # Create columns for better layout
                sdg_cols = st.columns(2)
                selected_sdgs = []
                
                for i, sdg in enumerate(SDG_LIST):
                    col_idx = i % 2
                    with sdg_cols[col_idx]:
                        # Disable checkbox if already 2 selected and this one isn't selected
                        disabled = len(st.session_state.selected_sdgs_research) >= 2 and sdg not in st.session_state.selected_sdgs_research
                        
                        is_checked = st.checkbox(
                            sdg,
                            value=sdg in st.session_state.selected_sdgs_research,
                            disabled=disabled,
                            key=f"sdg_research_manual_{sdg}"
                        )
                        
                        if is_checked:
                            selected_sdgs.append(sdg)
                
                # Update session state
                st.session_state.selected_sdgs_research = selected_sdgs
                
                # Show selection count
                if len(selected_sdgs) > 0:
                    st.success(f"✅ Selected {len(selected_sdgs)}/2 SDGs: {', '.join(selected_sdgs)}")
                else:
                    st.info("Please select at least 1 SDG")
            
            # Problem input
            problem = st.text_area(
                "Problem Statement:",
                placeholder="Describe the problem you want to address...",
                height=100,
                key="research_problem"
            )
            
            # Idea input
            idea = st.text_area(
                "Solution Idea:",
                placeholder="Describe your solution idea...",
                height=100,
                key="research_idea"
            )
        
        with col2:
            # Target market
            target_market = st.text_input(
                "Target Market:",
                placeholder="e.g., Small farmers in rural India"
            )
            
            # Research question
            research_question = st.text_area(
                "Research Question:",
                placeholder="What specific market insights do you want to discover?",
                height=100
            )
        
        # Generate research button
        if st.button("🚀 Generate Market Research", type="primary", use_container_width=True):
            # Get selected SDGs from session state
            selected_sdgs = st.session_state.get('selected_sdgs_research', [])
            
            # Validation
            if not target_market or not research_question:
                st.error("Please fill in Target Market and Research Question")
            elif not selected_sdgs:
                st.error("Please select at least one SDG")
            elif len(selected_sdgs) > 2:
                st.error("Please select maximum 2 SDGs only")
            elif not problem or not idea:
                st.error("Please provide both Problem Statement and Solution Idea")
            else:
                # Generate research
                results = generate_research(
                    sdgs=selected_sdgs,
                    problem=problem,
                    idea=idea,
                    target_market=target_market,
                    research_question=research_question
                )
                
                if results:
                    # Store results in session state for use in question generation
                    st.session_state.research_results = results
                    
                    # Display results
                    st.header("📈 Research Results")
                    
                    # Summary section
                    with st.container():
                        st.subheader("📋 Research Summary")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write("**Problem:**", results["problem"])
                            st.write("**Solution Idea:**", results["idea"])
                            st.write("**Target Market:**", results["target_market"])
                        with col2:
                            st.write("**SDGs:**", ", ".join(results["sdgs"]))
                            st.write("**Research Question:**", results["research_question"])
                    
                    # Web summary
                    with st.expander("🌐 Web Research Summary", expanded=True):
                        st.write(results["web_summary"])
                        if results["web_sources"]:
                            st.subheader("Sources:")
                            for i, url in enumerate(results["web_sources"], 1):
                                st.write(f"{i}. {url}")
                    
                    # Market research insights
                    with st.expander("📊 Market Research Insights", expanded=True):
                        st.write(results["market_research"])
                    
                    # Competitor insights
                    with st.expander("🏢 Competitor Analysis", expanded=True):
                        st.write(results["competitor_insights"])
    
    with tab2:
        st.header("❓ Student Question Generator")
        
        # Question generation options
        question_mode = st.radio(
            "Choose question generation mode:",
            ["📊 Based on Market Research", "🎯 Based on SDGs Only"],
            horizontal=True
        )
        
        if question_mode == "📊 Based on Market Research":
            st.subheader("Generate Questions from Market Research")
            
            # Check if we have research results
            if 'research_results' in st.session_state:
                results = st.session_state.research_results
                
                # Display current research data
                with st.expander("📋 Current Research Data", expanded=False):
                    st.write("**Problem:**", results["problem"])
                    st.write("**Solution Idea:**", results["idea"])
                    st.write("**Market Research:**", results["market_research"][:200] + "..." if len(results["market_research"]) > 200 else results["market_research"])
                
                # Generate questions button
                if st.button("🎯 Generate Questions from Research", type="primary", use_container_width=True):
                    questions = generate_student_questions(
                        problem=results["problem"],
                        idea=results["idea"],
                        market_research=results["market_research"]
                    )
                    
                    if questions:
                        st.session_state.generated_questions = questions
                        st.session_state.question_metadata = {
                            "type": "market_research",
                            "problem": results["problem"],
                            "idea": results["idea"],
                            "market_research": results["market_research"]
                        }
            else:
                st.info("💡 Generate market research first in the 'Market Research' tab to use this option.")
                
                # Alternative: Manual input
                st.subheader("Or Enter Research Data Manually:")
                
                col1, col2 = st.columns(2)
                with col1:
                    manual_problem = st.text_area(
                        "Problem Statement:",
                        placeholder="Describe the problem...",
                        height=100,
                        key="manual_problem"
                    )
                    manual_idea = st.text_area(
                        "Solution Idea:",
                        placeholder="Describe your solution...",
                        height=100,
                        key="manual_idea"
                    )
                
                with col2:
                    manual_research = st.text_area(
                        "Market Research Findings:",
                        placeholder="Enter your market research insights...",
                        height=200,
                        key="manual_research"
                    )
                
                if st.button("🎯 Generate Questions from Manual Input", type="secondary", use_container_width=True):
                    if manual_problem and manual_idea and manual_research:
                        questions = generate_student_questions(
                            problem=manual_problem,
                            idea=manual_idea,
                            market_research=manual_research
                        )
                        
                        if questions:
                            st.session_state.generated_questions = questions
                            st.session_state.question_metadata = {
                                "type": "manual_input",
                                "problem": manual_problem,
                                "idea": manual_idea,
                                "market_research": manual_research
                            }
                    else:
                        st.error("Please fill in all fields (Problem, Idea, and Market Research)")
        
        else:  # SDG-based questions
            st.subheader("Generate Questions Based on SDGs")
            
            # Initialize session state for question SDGs
            if 'selected_sdgs_questions' not in st.session_state:
                st.session_state.selected_sdgs_questions = []
            
            # SDG selection with smart validation using checkboxes
            st.write("**Select SDGs for Question Generation (Maximum 2):**")
            st.write("🎯 Choose up to 2 SDGs for focused questions")
            
            # Create columns for better layout
            sdg_cols = st.columns(2)
            selected_question_sdgs = []
            
            for i, sdg in enumerate(SDG_LIST):
                col_idx = i % 2
                with sdg_cols[col_idx]:
                    # Disable checkbox if already 2 selected and this one isn't selected
                    disabled = len(st.session_state.selected_sdgs_questions) >= 2 and sdg not in st.session_state.selected_sdgs_questions
                    
                    is_checked = st.checkbox(
                        sdg,
                        value=sdg in st.session_state.selected_sdgs_questions,
                        disabled=disabled,
                        key=f"sdg_questions_{sdg}"
                    )
                    
                    if is_checked:
                        selected_question_sdgs.append(sdg)
            
            # Update session state
            st.session_state.selected_sdgs_questions = selected_question_sdgs
            
            # Show selection count
            if len(selected_question_sdgs) > 0:
                st.success(f"✅ Selected {len(selected_question_sdgs)}/2 SDGs: {', '.join(selected_question_sdgs)}")
            else:
                st.info("Please select at least 1 SDG")
            
            # Clear selections button
            if st.button("🗑️ Clear SDG Selection", type="secondary"):
                st.session_state.selected_sdgs_questions = []
                st.rerun()
            
            # Optional context
            sdg_context = st.text_area(
                "Additional Context (Optional):",
                placeholder="Any specific context or focus area for the questions...",
                height=100
            )
            
            if st.button("🎯 Generate SDG Questions", type="primary", use_container_width=True):
                # Get selected SDGs from session state
                selected_question_sdgs = st.session_state.get('selected_sdgs_questions', [])
                
                if not selected_question_sdgs:
                    st.error("Please select at least one SDG")
                elif len(selected_question_sdgs) > 2:
                    st.error("Please select maximum 2 SDGs only")
                else:
                    questions = generate_sdg_questions(
                        selected_sdgs=selected_question_sdgs,
                        context=sdg_context
                    )
                    
                    if questions:
                        st.session_state.generated_questions = questions
                        st.session_state.question_metadata = {
                            "type": "sdg_based",
                            "selected_sdgs": selected_question_sdgs,
                            "context": sdg_context
                        }
        
        # Display generated questions
        if 'generated_questions' in st.session_state:
            st.header("📝 Generated Questions")
            
            questions = st.session_state.generated_questions
            metadata = st.session_state.get('question_metadata', {})
            
            # Display questions with edit capability
            st.subheader("Questions for Your Presentation:")
            
            edited_questions = []
            for i, question in enumerate(questions):
                edited_question = st.text_input(
                    f"Question {i+1}:",
                    value=question,
                    key=f"question_{i}"
                )
                edited_questions.append(edited_question)
            
            # Update questions in session state
            st.session_state.generated_questions = edited_questions
            
            # Add custom question
            st.subheader("Add Custom Question:")
            custom_question = st.text_input("Enter your custom question:")
            if st.button("➕ Add Custom Question"):
                if custom_question.strip():
                    st.session_state.generated_questions.append(custom_question.strip())
                    st.rerun()
            
            # Download questions
            st.subheader("📥 Download Questions")
            
            # Prepare download content
            download_content = "STUDENT PRESENTATION QUESTIONS\n"
            download_content += "=" * 50 + "\n\n"
            
            if metadata.get("type") == "market_research":
                download_content += f"Problem: {metadata.get('problem', 'N/A')}\n"
                download_content += f"Solution Idea: {metadata.get('idea', 'N/A')}\n"
                download_content += f"Market Research: {metadata.get('market_research', 'N/A')[:200]}...\n\n"
            elif metadata.get("type") == "sdg_based":
                download_content += f"Selected SDGs: {', '.join(metadata.get('selected_sdgs', []))}\n"
                download_content += f"Context: {metadata.get('context', 'N/A')}\n\n"
            
            download_content += "QUESTIONS TO ASK YOUR AUDIENCE:\n"
            download_content += "-" * 40 + "\n"
            
            for i, question in enumerate(edited_questions, 1):
                download_content += f"{i}. {question}\n"
            
            st.download_button(
                label="📥 Download Questions",
                data=download_content,
                file_name="student_presentation_questions.txt",
                mime="text/plain"
            )
            
            # Clear questions
            if st.button("🗑️ Clear Questions"):
                if 'generated_questions' in st.session_state:
                    del st.session_state.generated_questions
                if 'question_metadata' in st.session_state:
                    del st.session_state.question_metadata
                st.rerun()
    
    with tab3:
        st.header("📊 Market Fit Evaluator")
        st.markdown("### ✍ Student Prompt:")
        st.info("*Write why you believe your idea is needed in the market and how your idea is unique. Use any data or current knowledge you have. Outline how you will enter the market.*")
        
        student_input = st.text_area("Your Response", height=300, key="market_fit_response")
        
        if st.button("Give me some feedback", type="primary", use_container_width=True):
            if not student_input.strip():
                st.warning("Please enter your response before clicking the button.")
            else:
                with st.spinner("Analyzing your answer..."):
                    feedback = evaluate_student_response(student_input)
                    st.success("✅ Feedback generated!")
                    st.markdown("### 📋 Feedback Based on Rubric:")
                    st.markdown(feedback)

if __name__ == "__main__":
    main()
    