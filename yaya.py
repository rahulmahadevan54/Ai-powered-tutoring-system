import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, simpledialog
import openai
import json
import time
import os
import threading
import random
import hashlib
import datetime
import sqlite3
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk, ImageOps
import speech_recognition as sr
import pyttsx3
import requests
from io import BytesIO
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging
from abc import ABC, abstractmethod

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tutoring_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Modern UI Constants
PRIMARY_COLOR = "#4a6fa5"  # Deep blue
SECONDARY_COLOR = "#6b8cae"  # Lighter blue
ACCENT_COLOR = "#ff7e5f"  # Coral accent
LIGHT_BG = "#f8f9fa"  # Off-white background
DARK_TEXT = "#2d3748"  # Dark gray text
LIGHT_TEXT = "#f8f9fa"  # Light text
CARD_COLOR = "#ffffff"  # White cards
SHADOW_COLOR = "#e2e8f0"  # Light shadow

# Modern rounded button style
def create_rounded_button(parent, text, command, bg=PRIMARY_COLOR, fg=LIGHT_TEXT, radius=25, width=None):
    frame = tk.Frame(parent, bg=LIGHT_BG, width=width)
    frame.pack_propagate(False)
    
    button = tk.Button(
        frame, 
        text=text, 
        command=command,
        bg=bg,
        fg=fg,
        borderwidth=0,
        highlightthickness=0,
        relief="flat",
        activebackground=SECONDARY_COLOR,
        activeforeground=LIGHT_TEXT,
        font=("Segoe UI", 10)
    )
    button.pack(fill="both", expand=True, padx=5, pady=5)
    
    # Create rounded effect
    frame.config(highlightbackground=bg, highlightthickness=1)
    frame.bind("<Enter>", lambda e: frame.config(highlightbackground=SECONDARY_COLOR))
    frame.bind("<Leave>", lambda e: frame.config(highlightbackground=bg))
    
    return frame

# Modern card container
class Card(tk.Frame):
    def __init__(self, parent, title="", **kwargs):
        super().__init__(parent, bg=CARD_COLOR, bd=0, highlightbackground=SHADOW_COLOR, 
                         highlightthickness=1, highlightcolor=SHADOW_COLOR, **kwargs)
        
        if title:
            title_frame = tk.Frame(self, bg=CARD_COLOR)
            title_frame.pack(fill="x", padx=10, pady=(10, 5))
            tk.Label(
                title_frame, 
                text=title, 
                font=("Segoe UI", 12, "bold"), 
                bg=CARD_COLOR, 
                fg=DARK_TEXT
            ).pack(side="left")
            
        self.content_frame = tk.Frame(self, bg=CARD_COLOR)
        self.content_frame.pack(fill="both", expand=True, padx=10, pady=5)

# Modern entry field
class ModernEntry(tk.Entry):
    def __init__(self, parent, placeholder="", **kwargs):
        super().__init__(
            parent, 
            bd=0, 
            bg=CARD_COLOR, 
            fg=DARK_TEXT, 
            highlightthickness=1, 
            highlightbackground=SECONDARY_COLOR,
            highlightcolor=PRIMARY_COLOR,
            insertbackground=PRIMARY_COLOR,
            font=("Segoe UI", 10),
            **kwargs
        )
        
        self.placeholder = placeholder
        self.insert(0, placeholder)
        self.bind("<FocusIn>", self._clear_placeholder)
        self.bind("<FocusOut>", self._add_placeholder)
        self.config(fg="#a0aec0")  # Light gray placeholder
        
    def _clear_placeholder(self, event):
        if self.get() == self.placeholder:
            self.delete(0, tk.END)
            self.config(fg=DARK_TEXT)
            
    def _add_placeholder(self, event):
        if not self.get():
            self.insert(0, self.placeholder)
            self.config(fg="#a0aec0")  # Light gray placeholder

# Modern scrollable text
class ModernScrolledText(scrolledtext.ScrolledText):
    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            bg=CARD_COLOR,
            fg=DARK_TEXT,
            bd=0,
            highlightthickness=1,
            highlightbackground=SECONDARY_COLOR,
            highlightcolor=PRIMARY_COLOR,
            insertbackground=PRIMARY_COLOR,
            **kwargs
        )
        
        # Custom scrollbar style
        self.vbar.config(troughcolor=LIGHT_BG, background=SECONDARY_COLOR, 
                        activebackground=PRIMARY_COLOR, bordercolor=LIGHT_BG)

# Modern radio button
class ModernRadioButton(tk.Radiobutton):
    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            bg=LIGHT_BG,
            fg=DARK_TEXT,
            activebackground=LIGHT_BG,
            activeforeground=DARK_TEXT,
            selectcolor=LIGHT_BG,
            font=("Segoe UI", 10),
            **kwargs
        )

# Modern whiteboard
class ModernWhiteboard(tk.Canvas):
    def __init__(self, master, **kwargs):
        super().__init__(master, bg=CARD_COLOR, bd=0, highlightthickness=1,
                        highlightbackground=SECONDARY_COLOR, highlightcolor=PRIMARY_COLOR, **kwargs)
        self.drawing = False
        self.last_x = 0
        self.last_y = 0
        self.elements = []
        self.current_color = PRIMARY_COLOR
        self.current_tool = "pen"
        self.line_width = 2
        
        # Tool panel with modern styling
        self.tool_panel = tk.Frame(master, bg=LIGHT_BG)
        self.tool_panel.pack(side="top", fill="x", pady=(0, 5))
        
        tools = [
            ("Pen", "pen"),
            ("Line", "line"),
            ("Rectangle", "rectangle"),
            ("Oval", "oval"),
            ("Text", "text"),
            ("Eraser", "eraser")
        ]
        
        for text, tool in tools:
            btn = create_rounded_button(
                self.tool_panel,
                text,
                lambda t=tool: self.set_tool(t),
                bg=SECONDARY_COLOR if tool == "pen" else LIGHT_BG,
                fg=DARK_TEXT if tool != "pen" else LIGHT_TEXT,
                radius=15
            )
            btn.pack(side="left", padx=2, pady=2)
        
        # Color palette
        self.color_palette = tk.Frame(master, bg=LIGHT_BG)
        self.color_palette.pack(side="top", fill="x", pady=(0, 10))
        
        colors = [PRIMARY_COLOR, ACCENT_COLOR, "#4fd1c5", "#f6ad55", "#9f7aea", "#68d391"]
        for color in colors:
            color_btn = tk.Canvas(
                self.color_palette,
                width=25,
                height=25,
                bg=color,
                bd=0,
                highlightthickness=0
            )
            color_btn.bind("<Button-1>", lambda e, c=color: self.set_color(c))
            color_btn.pack(side="left", padx=2)
            
        # Bind events
        self.bind("<Button-1>", self.start_draw)
        self.bind("<B1-Motion>", self.draw)
        self.bind("<ButtonRelease-1>", self.stop_draw)
        
    def set_tool(self, tool):
        self.current_tool = tool
        # Update button styles
        for child in self.tool_panel.winfo_children():
            if isinstance(child, tk.Frame):
                for subchild in child.winfo_children():
                    if isinstance(subchild, tk.Button):
                        if tool in subchild.cget("command").__code__.co_freevars:
                            child.config(highlightbackground=SECONDARY_COLOR)
                            subchild.config(bg=SECONDARY_COLOR, fg=LIGHT_TEXT)
                        else:
                            child.config(highlightbackground=LIGHT_BG)
                            subchild.config(bg=LIGHT_BG, fg=DARK_TEXT)
        
    def set_color(self, color):
        self.current_color = color
        
    def start_draw(self, event):
        self.drawing = True
        self.last_x = event.x
        self.last_y = event.y
        
        if self.current_tool == "text":
            text = simpledialog.askstring("Text", "Enter text:")
            if text:
                item = self.create_text(event.x, event.y, text=text, fill=self.current_color, 
                                      font=("Segoe UI", 10))
                self.elements.append({
                    "type": "text",
                    "x": event.x,
                    "y": event.y,
                    "text": text,
                    "color": self.current_color,
                    "font": "Segoe UI 10"
                })
        
    def draw(self, event):
        if not self.drawing:
            return
            
        if self.current_tool == "pen":
            self.create_line(self.last_x, self.last_y, event.x, event.y, 
                            fill=self.current_color, width=self.line_width)
            self.elements.append({
                "type": "line",
                "x1": self.last_x,
                "y1": self.last_y,
                "x2": event.x,
                "y2": event.y,
                "color": self.current_color,
                "width": self.line_width
            })
            
        self.last_x = event.x
        self.last_y = event.y
        
    def stop_draw(self, event):
        if self.current_tool == "line":
            item = self.create_line(self.last_x, self.last_y, event.x, event.y, 
                                  fill=self.current_color, width=self.line_width)
            self.elements.append({
                "type": "line",
                "x1": self.last_x,
                "y1": self.last_y,
                "x2": event.x,
                "y2": event.y,
                "color": self.current_color,
                "width": self.line_width
            })
        elif self.current_tool == "rectangle":
            item = self.create_rectangle(self.last_x, self.last_y, event.x, event.y,
                                       outline=self.current_color, width=self.line_width)
            self.elements.append({
                "type": "rectangle",
                "x1": self.last_x,
                "y1": self.last_y,
                "x2": event.x,
                "y2": event.y,
                "color": self.current_color,
                "width": self.line_width
            })
        elif self.current_tool == "oval":
            item = self.create_oval(self.last_x, self.last_y, event.x, event.y,
                                  outline=self.current_color, width=self.line_width)
            self.elements.append({
                "type": "oval",
                "x1": self.last_x,
                "y1": self.last_y,
                "x2": event.x,
                "y2": event.y,
                "color": self.current_color,
                "width": self.line_width
            })
        elif self.current_tool == "eraser":
            self.create_rectangle(event.x-10, event.y-10, event.x+10, event.y+10,
                                outline=CARD_COLOR, fill=CARD_COLOR)
            
        self.drawing = False
        
    def clear(self):
        self.delete("all")
        self.elements = []
        
    def load_elements(self, elements):
        self.clear()
        for element in elements:
            if element["type"] == "line":
                self.create_line(element["x1"], element["y1"], element["x2"], element["y2"],
                                fill=element["color"], width=element["width"])
            elif element["type"] == "rectangle":
                self.create_rectangle(element["x1"], element["y1"], element["x2"], element["y2"],
                                    outline=element["color"], width=element["width"])
            elif element["type"] == "oval":
                self.create_oval(element["x1"], element["y1"], element["x2"], element["y2"],
                               outline=element["color"], width=element["width"])
            elif element["type"] == "text":
                font = element.get("font", "Segoe UI 10")
                self.create_text(element["x"], element["y"], text=element["text"],
                               fill=element["color"], font=font)

@dataclass
class UserProfile:
    user_id: str
    name: str
    learning_style: str
    proficiency_level: str
    preferred_subjects: List[str]
    session_history: List[Dict]
    avatar_path: str = ""

@dataclass
class TutoringSession:
    session_id: str
    user_id: str
    subject: str
    start_time: str
    end_time: Optional[str] = None
    context: str = ""
    messages: List[Dict] = None
    learning_objectives: List[str] = None
    whiteboard_data: List[Dict] = None

    def __post_init__(self):
        if self.messages is None:
            self.messages = []
        if self.learning_objectives is None:
            self.learning_objectives = []
        if self.whiteboard_data is None:
            self.whiteboard_data = []

class KnowledgeBase(ABC):
    @abstractmethod
    def get_subject_resources(self, subject: str) -> List[Dict]:
        pass

    @abstractmethod
    def update_knowledge_base(self, subject: str, content: Dict) -> bool:
        pass

class LocalKnowledgeBase(KnowledgeBase):
    def __init__(self, db_path: str = "knowledge_base.db"):
        self.db_path = db_path
        self._initialize_db()

    def _initialize_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subjects (
                    subject_id TEXT PRIMARY KEY,
                    subject_name TEXT NOT NULL,
                    description TEXT,
                    last_updated TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS resources (
                    resource_id TEXT PRIMARY KEY,
                    subject_id TEXT,
                    title TEXT NOT NULL,
                    content_type TEXT,
                    content TEXT,
                    difficulty_level TEXT,
                    FOREIGN KEY (subject_id) REFERENCES subjects (subject_id)
                )
            """)
            conn.commit()

    def get_subject_resources(self, subject: str) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT r.title, r.content_type, r.content, r.difficulty_level
                FROM resources r
                JOIN subjects s ON r.subject_id = s.subject_id
                WHERE s.subject_name = ?
            """, (subject,))
            rows = cursor.fetchall()
            return [{
                'title': row[0],
                'type': row[1],
                'content': row[2],
                'difficulty': row[3]
            } for row in rows]

    def update_knowledge_base(self, subject: str, content: Dict) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if subject exists
                cursor.execute("SELECT subject_id FROM subjects WHERE subject_name = ?", (subject,))
                subject_row = cursor.fetchone()
                
                if not subject_row:
                    subject_id = hashlib.md5(subject.encode()).hexdigest()
                    cursor.execute(
                        "INSERT INTO subjects VALUES (?, ?, ?, ?)",
                        (subject_id, subject, f"Resources for {subject}", datetime.datetime.now().isoformat())
                    )
                else:
                    subject_id = subject_row[0]
                
                # Insert/update resource
                resource_id = hashlib.md5(content['title'].encode()).hexdigest()
                cursor.execute(
                    """INSERT OR REPLACE INTO resources VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        resource_id,
                        subject_id,
                        content['title'],
                        content.get('type', 'text'),
                        content['content'],
                        content.get('difficulty', 'intermediate')
                    )
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating knowledge base: {e}")
            return False

class TutoringEngine:
    def __init__(self, api_key: str, knowledge_base: KnowledgeBase):
        openai.api_key = api_key
        self.knowledge_base = knowledge_base
        self.sessions: Dict[str, TutoringSession] = {}
        self.user_profiles: Dict[str, UserProfile] = {}
        self.speech_engine = pyttsx3.init()
        self.voice_recognizer = sr.Recognizer()
        self.load_user_data()

    def load_user_data(self):
        """Load user profiles and sessions from database"""
        try:
            with sqlite3.connect("user_data.db") as conn:
                cursor = conn.cursor()
                
                # Create tables if not exists
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id TEXT PRIMARY KEY,
                        name TEXT,
                        learning_style TEXT,
                        proficiency_level TEXT,
                        preferred_subjects TEXT,
                        session_history TEXT,
                        avatar_path TEXT
                    )
                """)
                
                # Load users
                cursor.execute("SELECT * FROM users")
                users = cursor.fetchall()
                for user in users:
                    self.user_profiles[user[0]] = UserProfile(
                        user_id=user[0],
                        name=user[1],
                        learning_style=user[2],
                        proficiency_level=user[3],
                        preferred_subjects=json.loads(user[4]),
                        session_history=json.loads(user[5]),
                        avatar_path=user[6]
                    )
                
                logger.info(f"Loaded {len(self.user_profiles)} user profiles")
        except Exception as e:
            logger.warning(f"Could not load user data: {e}")

    def save_user_data(self):
        """Save user profiles and sessions to database"""
        try:
            with sqlite3.connect("user_data.db") as conn:
                cursor = conn.cursor()
                
                # Save all users
                for user_id, profile in self.user_profiles.items():
                    cursor.execute(
                        """INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (
                            user_id,
                            profile.name,
                            profile.learning_style,
                            profile.proficiency_level,
                            json.dumps(profile.preferred_subjects),
                            json.dumps(profile.session_history),
                            profile.avatar_path
                        )
                    )
                
                conn.commit()
                logger.info(f"Saved {len(self.user_profiles)} user profiles")
        except Exception as e:
            logger.error(f"Error saving user data: {e}")

    def start_session(self, user_id: str, subject: str) -> TutoringSession:
        """Initialize a new tutoring session"""
        session_id = hashlib.sha256(
            f"{user_id}{subject}{datetime.datetime.now().isoformat()}".encode()
        ).hexdigest()
        
        session = TutoringSession(
            session_id=session_id,
            user_id=user_id,
            subject=subject,
            start_time=datetime.datetime.now().isoformat(),
            learning_objectives=self._generate_learning_objectives(subject)
        )
        
        self.sessions[session_id] = session
        logger.info(f"Started new session {session_id} for user {user_id}")
        return session

    def _generate_learning_objectives(self, subject: str) -> List[str]:
        """Generate learning objectives for the subject"""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": f"Generate 3-5 key learning objectives for {subject} for K-12 students considering different learning styles."},
                    {"role": "user", "content": f"List the most important learning objectives for studying {subject} at K-12 level."}
                ],
                temperature=0.7
            )
            objectives = response.choices[0].message["content"].split('\n')
            return [obj.strip() for obj in objectives if obj.strip()]
        except Exception as e:
            logger.error(f"Error generating learning objectives: {e}")
            return [
                f"Understand core concepts of {subject}",
                f"Apply {subject} knowledge to solve problems",
                f"Develop critical thinking in {subject}"
            ]

    def get_tutoring_response(self, session_id: str, user_query: str) -> Tuple[str, Optional[List[str]]]:
        """Get AI response for user query with contextual follow-ups"""
        if session_id not in self.sessions:
            raise ValueError("Invalid session ID")
            
        session = self.sessions[session_id]
        context = "\n".join([msg['content'] for msg in session.messages[-5:]])
        
        try:
            # Get relevant resources from knowledge base
            resources = self.knowledge_base.get_subject_resources(session.subject)
            resources_context = "\n".join(
                f"Resource: {res['title']}\nContent: {res['content'][:200]}..."
                for res in resources[:3]
            )
            
            # Get user profile for personalized learning
            user_profile = self.user_profiles.get(session.user_id, None)
            learning_style = user_profile.learning_style if user_profile else "unknown"
            
            # Generate AI response with more detailed instructions
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": f"""
                        You are an expert K-12 tutor in {session.subject}. 
                        Current learning objectives: {', '.join(session.learning_objectives)}
                        Available resources: {resources_context}
                        Student learning style: {learning_style}
                        
                        Provide detailed, educational responses that:
                        - Explain concepts clearly using age-appropriate language
                        - Use {learning_style} learning style techniques
                        - Provide real-world examples relevant to students
                        - Include visual descriptions when appropriate
                        - Break down complex ideas into simpler parts
                        - Encourage critical thinking with probing questions
                        - Suggest hands-on activities when applicable
                        - Relate concepts to student interests when possible
                    """},
                    *session.messages[-5:],
                    {"role": "user", "content": user_query}
                ],
                temperature=0.7
            )
            
            ai_response = response.choices[0].message["content"]
            
            # Update session context
            session.messages.append({"role": "user", "content": user_query})
            session.messages.append({"role": "assistant", "content": ai_response})
            
            # Generate follow-up questions
            followups = self._generate_followup_questions(session.subject, ai_response)
            
            return ai_response, followups
            
        except Exception as e:
            logger.error(f"Error generating tutoring response: {e}")
            return f"An error occurred: {str(e)}", None

    def _generate_followup_questions(self, subject: str, context: str) -> List[str]:
        """Generate relevant follow-up questions"""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": f"Generate 3 insightful follow-up questions about {subject} for K-12 students."},
                    {"role": "user", "content": f"Based on this context: {context}\n\nGenerate 3 follow-up questions that would deepen understanding of {subject} for K-12 students."}
                ],
                temperature=0.7
            )
            questions = response.choices[0].message["content"].split('\n')
            return [q.strip() for q in questions if q.strip()][:3]
        except Exception as e:
            logger.error(f"Error generating follow-up questions: {e}")
            return []

    def generate_quiz(self, session_id: str, difficulty: str = "medium") -> Dict:
        """Generate a quiz question for the session"""
        if session_id not in self.sessions:
            raise ValueError("Invalid session ID")
            
        session = self.sessions[session_id]
        
        try:
            prompt = f"""
                Generate a {difficulty} difficulty multiple-choice quiz question about {session.subject} 
                with 4 options and specify the correct answer. The question should relate to these 
                learning objectives: {', '.join(session.learning_objectives)} and be appropriate for K-12 students.
                
                Format your response as JSON with these fields:
                - question: the question text
                - options: list of 4 options
                - correct_answer: index of correct option (0-3)
                - explanation: brief explanation of the answer
                - visual_description: description of an image that could help explain the concept
            """
            
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a quiz generator for K-12 students. Provide well-formatted JSON output."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                response_format={"type": "json_object"}
            )
            
            quiz_data = json.loads(response.choices[0].message["content"])
            return quiz_data
            
        except Exception as e:
            logger.error(f"Error generating quiz: {e}")
            return {
                "question": f"What is a key concept in {session.subject}?",
                "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
                "correct_answer": 0,
                "explanation": "Basic concept explanation.",
                "visual_description": "An illustration showing the basic concept"
            }

    def generate_whiteboard_content(self, concept: str) -> Dict:
        """Generate whiteboard content for a concept"""
        try:
            prompt = f"""
                Generate content for an interactive whiteboard to explain: {concept} to K-12 students.
                Provide a JSON response with:
                - title: short title
                - explanation: detailed explanation
                - visual_elements: list of elements to draw (shapes, text, arrows)
                - animation_sequence: how to animate the explanation
                - color_scheme: suggested colors
                - learning_activities: suggested hands-on activities
            """
            
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a whiteboard content generator for K-12 education."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message["content"])
            
        except Exception as e:
            logger.error(f"Error generating whiteboard content: {e}")
            return {
                "title": concept,
                "explanation": f"Explanation of {concept}",
                "visual_elements": [],
                "animation_sequence": [],
                "color_scheme": ["#3498db", "#e74c3c", "#2ecc71"],
                "learning_activities": []
            }

    def text_to_speech(self, text: str):
        """Convert text to speech"""
        self.speech_engine.say(text)
        self.speech_engine.runAndWait()

    def speech_to_text(self) -> Optional[str]:
        """Convert speech to text"""
        with sr.Microphone() as source:
            print("Listening...")
            audio = self.voice_recognizer.listen(source)
            
            try:
                text = self.voice_recognizer.recognize_google(audio)
                return text
            except Exception as e:
                logger.error(f"Speech recognition error: {e}")
                return None

    def end_session(self, session_id: str) -> Dict:
        """End a tutoring session and return summary"""
        if session_id not in self.sessions:
            raise ValueError("Invalid session ID")
            
        session = self.sessions[session_id]
        session.end_time = datetime.datetime.now().isoformat()
        
        # Generate session summary
        summary = self._generate_session_summary(session)
        
        # Update user profile
        if session.user_id in self.user_profiles:
            self.user_profiles[session.user_id].session_history.append({
                "session_id": session_id,
                "subject": session.subject,
                "start_time": session.start_time,
                "end_time": session.end_time,
                "learning_objectives": session.learning_objectives,
                "topics_covered": summary['topics_covered'],
                "performance_rating": summary['performance_rating']
            })
        
        # Save data
        self.save_user_data()
        
        return summary

    def _generate_session_summary(self, session: TutoringSession) -> Dict:
        """Generate a summary of the session"""
        try:
            messages_text = "\n".join(
                f"{msg['role']}: {msg['content']}" 
                for msg in session.messages
            )
            
            prompt = f"""
                Analyze this K-12 tutoring session and generate a comprehensive summary:
                Subject: {session.subject}
                Learning Objectives: {', '.join(session.learning_objectives)}
                
                Conversation:
                {messages_text}
                
                Provide a JSON response with these fields:
                - topics_covered: list of main topics discussed
                - key_learnings: 3-5 key takeaways
                - suggested_next_steps: recommendations for future study
                - performance_rating: 1-5 rating of student engagement
                - areas_for_improvement: concepts needing more work
                - learning_style_insights: observations about learning style
                - recommended_resources: suggested learning materials
            """
            
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a session analyzer for K-12 education. Provide well-formatted JSON output."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message["content"])
            
        except Exception as e:
            logger.error(f"Error generating session summary: {e}")
            return {
                "topics_covered": [f"Core concepts of {session.subject}"],
                "key_learnings": [
                    f"Introduction to {session.subject}",
                    "Basic principles and concepts"
                ],
                "suggested_next_steps": [
                    f"Review basic {session.subject} concepts",
                    "Practice with more examples"
                ],
                "performance_rating": 3,
                "areas_for_improvement": [f"Advanced {session.subject} concepts"],
                "learning_style_insights": "Visual learning seemed effective",
                "recommended_resources": []
            }

class ModernTutoringApp:
    def __init__(self, root, engine: TutoringEngine):
        self.root = root
        self.engine = engine
        self.current_session = None
        self.current_user = None
        self.voice_thread = None
        self.stop_voice_event = threading.Event()
        self.voice_enabled = False
        
        # Configure main window
        self.root.title("EduMentor AI")
        self.root.geometry("1200x800")
        self.root.configure(bg=LIGHT_BG)
        
        # Check if we have any user profiles
        if not self.engine.user_profiles:
            self.show_profile_selection()
        else:
            self.create_main_menu()
        
    def show_profile_selection(self):
        """Display profile options when no profiles exist - FIXED VERSION"""
        self.clear_window()
    
     
    
    def create_main_menu(self):
        """Create modern main menu interface"""
        self.clear_window()
        
        # Header with logo
        header = tk.Frame(self.root, bg=PRIMARY_COLOR, height=100)
        header.pack(fill="x")
        
        # Logo and title
        logo_frame = tk.Frame(header, bg=PRIMARY_COLOR)
        logo_frame.pack(pady=20)
        
        # Placeholder for logo (replace with actual image)
        tk.Label(
            logo_frame,
            text="🧠",  # Replace with actual logo
            font=("Segoe UI", 24),
            bg=PRIMARY_COLOR,
            fg=LIGHT_TEXT
        ).pack(side="left", padx=10)
        
        tk.Label(
            logo_frame,
            text="EduMentor AI",
            font=("Segoe UI", 24, "bold"),
            bg=PRIMARY_COLOR,
            fg=LIGHT_TEXT
        ).pack(side="left")
        
        # Main content with gradient background
        content = tk.Frame(self.root, bg=LIGHT_BG)
        content.pack(expand=True, fill="both", padx=40, pady=40)
        
        # Welcome card
        welcome_card = Card(content, title="Welcome to EduMentor AI")
        welcome_card.pack(fill="x", pady=(0, 20))
        
        if self.current_user:
            greeting = f"Welcome back, {self.current_user.name}!"
        else:
            greeting = "Your personalized AI tutoring assistant"
            
        tk.Label(
            welcome_card.content_frame,
            text=greeting,
            font=("Segoe UI", 14),
            bg=CARD_COLOR,
            fg=DARK_TEXT
        ).pack(pady=10)
        
        # Action buttons
        action_frame = tk.Frame(content, bg=LIGHT_BG)
        action_frame.pack(fill="x", pady=20)
        
        if self.current_user and self.current_user.user_id.startswith("guest"):
            actions = [
                ("New Session", self.start_new_session, PRIMARY_COLOR),
                ("Create Profile", self.show_register, SECONDARY_COLOR),
                ("Exit", self.root.quit, "#e53e3e")
            ]
        else:
            actions = [
                ("New Session", self.start_new_session, PRIMARY_COLOR),
                ("Switch User", self.show_login, SECONDARY_COLOR),
                ("Exit", self.root.quit, "#e53e3e")
            ]
        
        for text, command, color in actions:
            btn = create_rounded_button(
                action_frame,
                text,
                command,
                bg=color,
                radius=20
            )
            btn.pack(side="left", expand=True, padx=10)
    
    def show_login(self):
        """Show modern login interface"""
        self.clear_window()
        
        # Header
        header = tk.Frame(self.root, bg=PRIMARY_COLOR, height=80)
        header.pack(fill="x")
        
        tk.Button(
            header,
            text="← Back",
            command=self.create_main_menu,
            bg=PRIMARY_COLOR,
            fg=LIGHT_TEXT,
            bd=0,
            font=("Segoe UI", 10)
        ).pack(side="left", padx=20)
        
        tk.Label(
            header,
            text="Login to Your Account",
            font=("Segoe UI", 18, "bold"),
            bg=PRIMARY_COLOR,
            fg=LIGHT_TEXT
        ).pack(side="left", padx=20)
        
        # Main content
        content = tk.Frame(self.root, bg=LIGHT_BG)
        content.pack(expand=True, fill="both", padx=100, pady=50)
        
        # Login card
        login_card = Card(content, title="Account Login")
        login_card.pack(fill="both", expand=True)
        
        # Form elements
        form_frame = tk.Frame(login_card.content_frame, bg=CARD_COLOR)
        form_frame.pack(pady=20, padx=40)
        
        tk.Label(
            form_frame,
            text="User ID:",
            font=("Segoe UI", 10),
            bg=CARD_COLOR,
            fg=DARK_TEXT
        ).pack(anchor="w", pady=(10, 5))
        
        self.login_id_entry = ModernEntry(form_frame, placeholder="Enter your user ID")
        self.login_id_entry.pack(fill="x", pady=5)
        
        tk.Label(
            form_frame,
            text="Password:",
            font=("Segoe UI", 10),
            bg=CARD_COLOR,
            fg=DARK_TEXT
        ).pack(anchor="w", pady=(10, 5))
        
        self.login_pw_entry = ModernEntry(form_frame, placeholder="Enter your password", show="•")
        self.login_pw_entry.pack(fill="x", pady=5)
        
        # Action buttons
        btn_frame = tk.Frame(form_frame, bg=CARD_COLOR)
        btn_frame.pack(fill="x", pady=20)
        
        create_rounded_button(
            btn_frame,
            "Login",
            self.do_login,
            bg=PRIMARY_COLOR,
            radius=20
        ).pack(side="left", padx=5)
        
        create_rounded_button(
            btn_frame,
            "Forgot Password",
            lambda: messagebox.showinfo("Info", "Please contact support"),
            bg=LIGHT_BG,
            fg=DARK_TEXT,
            radius=20
        ).pack(side="right", padx=5)
    
    def show_register(self):
        """Show modern registration interface"""
        self.clear_window()
        
        # Header
        header = tk.Frame(self.root, bg=PRIMARY_COLOR, height=80)
        header.pack(fill="x")
        
        tk.Button(
            header,
            text="← Back",
            command=self.create_main_menu if self.current_user else self.show_profile_selection,
            bg=PRIMARY_COLOR,
            fg=LIGHT_TEXT,
            bd=0,
            font=("Segoe UI", 10)
        ).pack(side="left", padx=20)
        
        tk.Label(
            header,
            text="Create New Account",
            font=("Segoe UI", 18, "bold"),
            bg=PRIMARY_COLOR,
            fg=LIGHT_TEXT
        ).pack(side="left", padx=20)
        
        # Main content
        content = tk.Frame(self.root, bg=LIGHT_BG)
        content.pack(expand=True, fill="both", padx=100, pady=50)
        
        # Registration card
        reg_card = Card(content, title="Account Registration")
        reg_card.pack(fill="both", expand=True)
        
        # Form elements
        form_frame = tk.Frame(reg_card.content_frame, bg=CARD_COLOR)
        form_frame.pack(pady=20, padx=40)
        
        tk.Label(
            form_frame,
            text="Full Name:",
            font=("Segoe UI", 10),
            bg=CARD_COLOR,
            fg=DARK_TEXT
        ).pack(anchor="w", pady=(10, 5))
        
        self.reg_name_entry = ModernEntry(form_frame, placeholder="Enter your full name")
        self.reg_name_entry.pack(fill="x", pady=5)
        
        tk.Label(
            form_frame,
            text="Learning Style:",
            font=("Segoe UI", 10),
            bg=CARD_COLOR,
            fg=DARK_TEXT
        ).pack(anchor="w", pady=(10, 5))
        
        style_frame = tk.Frame(form_frame, bg=CARD_COLOR)
        style_frame.pack(fill="x", pady=5)
        
        self.reg_style_var = tk.StringVar(value="visual")
        styles = [
            ("Visual", "visual"),
            ("Auditory", "auditory"),
            ("Kinesthetic", "kinesthetic")
        ]
        
        for text, value in styles:
            ModernRadioButton(
                style_frame,
                text=text,
                variable=self.reg_style_var,
                value=value,
                command=lambda: None
            ).pack(side="left", padx=10)
        
        tk.Label(
            form_frame,
            text="Proficiency Level:",
            font=("Segoe UI", 10),
            bg=CARD_COLOR,
            fg=DARK_TEXT
        ).pack(anchor="w", pady=(10, 5))
        
        level_frame = tk.Frame(form_frame, bg=CARD_COLOR)
        level_frame.pack(fill="x", pady=5)
        
        self.reg_level_var = tk.StringVar(value="beginner")
        levels = [
            ("Beginner", "beginner"),
            ("Intermediate", "intermediate"),
            ("Advanced", "advanced")
        ]
        
        for text, value in levels:
            ModernRadioButton(
                level_frame,
                text=text,
                variable=self.reg_level_var,
                value=value,
                command=lambda: None
            ).pack(side="left", padx=10)
        
        # Register button
        btn_frame = tk.Frame(form_frame, bg=CARD_COLOR)
        btn_frame.pack(fill="x", pady=20)
        
        create_rounded_button(
            btn_frame,
            "Register",
            self.do_register,
            bg=PRIMARY_COLOR,
            radius=20
        ).pack(fill="x")
    
    def guest_login(self):
        """Login as guest"""
        user_id = "guest_" + str(random.randint(1000, 9999))
        self.current_user = UserProfile(
            user_id=user_id,
            name="Guest User",
            learning_style="unknown",
            proficiency_level="unknown",
            preferred_subjects=[],
            session_history=[]
        )
        self.create_main_menu()
    
    def do_login(self):
        """Perform login"""
        user_id = self.login_id_entry.get()
        password = self.login_pw_entry.get()  # In real app, would verify
        
        # Check if user exists
        if user_id in self.engine.user_profiles:
            self.current_user = self.engine.user_profiles[user_id]
            self.create_main_menu()
        else:
            messagebox.showerror("Error", "User not found. Please register.")
            self.show_register()
    
    def do_register(self):
        """Perform registration"""
        name = self.reg_name_entry.get()
        learning_style = self.reg_style_var.get()
        proficiency_level = self.reg_level_var.get()
        
        if not name:
            messagebox.showerror("Error", "Please enter your name")
            return
            
        user_id = hashlib.sha256(name.encode()).hexdigest()[:8]
        self.current_user = UserProfile(
            user_id=user_id,
            name=name,
            learning_style=learning_style,
            proficiency_level=proficiency_level,
            preferred_subjects=[],
            session_history=[]
        )
        
        # Add to engine
        self.engine.user_profiles[user_id] = self.current_user
        self.engine.save_user_data()
        
        messagebox.showinfo("Success", f"Account created! Your user ID is: {user_id}")
        self.create_main_menu()
    
    def show_dashboard(self):
        """Show user dashboard"""
        self.clear_window()
        
        # Header with user info
        header = tk.Frame(self.root, bg=PRIMARY_COLOR, height=80)
        header.pack(fill="x")
        
        user_info = tk.Frame(header, bg=PRIMARY_COLOR)
        user_info.pack(side="right", padx=20)
        
        tk.Label(user_info, text=f"Welcome, {self.current_user.name}", 
                font=("Segoe UI", 12), fg=LIGHT_TEXT, bg=PRIMARY_COLOR).pack(anchor="e")
        tk.Label(user_info, text=f"Learning Style: {self.current_user.learning_style}", 
                font=("Segoe UI", 10), fg=LIGHT_TEXT, bg=PRIMARY_COLOR).pack(anchor="e")
        
        # Back button
        tk.Button(
            header,
            text="Logout",
            command=self.create_main_menu,
            bg=ACCENT_COLOR,
            fg=LIGHT_TEXT,
            bd=0,
            font=("Segoe UI", 10)
        ).pack(side="left", padx=20)
        
        # Main content
        content = tk.Frame(self.root, bg=LIGHT_BG)
        content.pack(expand=True, fill="both", padx=20, pady=20)
        
        # Navigation sidebar
        sidebar = tk.Frame(content, bg=SECONDARY_COLOR, width=200)
        sidebar.pack(side="left", fill="y")
        
        nav_buttons = [
            ("New Session", self.start_new_session),
            ("Session History", self.show_session_history),
            ("Learning Analytics", self.show_analytics),
            ("Settings", self.show_settings),
            ("Exit", self.root.quit)
        ]
        
        for text, command in nav_buttons:
            btn = create_rounded_button(
                sidebar,
                text,
                command,
                bg=SECONDARY_COLOR,
                fg=LIGHT_TEXT,
                radius=15,
                width=180
            )
            btn.pack(pady=5, padx=5, fill="x")
        
        # Dashboard content
        dashboard = tk.Frame(content, bg=LIGHT_BG)
        dashboard.pack(expand=True, fill="both", padx=20, pady=20)
        
        tk.Label(dashboard, text="Dashboard", font=("Segoe UI", 16), 
                bg=LIGHT_BG).pack(pady=10)
        
        # Recent sessions
        if self.current_user.session_history:
            recent_frame = tk.Frame(dashboard, bg=LIGHT_BG)
            recent_frame.pack(fill="x", pady=10)
            
            tk.Label(recent_frame, text="Recent Sessions:", 
                    font=("Segoe UI", 12), bg=LIGHT_BG).pack(anchor="w")
            
            for session in self.current_user.session_history[-3:]:
                session_card = Card(recent_frame)
                session_card.pack(fill="x", pady=5)
                
                tk.Label(session_card.content_frame, 
                        text=f"{session['subject']} - {session['start_time'][:10]}", 
                        bg=CARD_COLOR).pack(side="left", padx=10)
                tk.Label(session_card.content_frame, 
                        text=f"Rating: {session.get('performance_rating', '?')}/5", 
                        bg=CARD_COLOR).pack(side="right", padx=10)
        else:
            tk.Label(dashboard, text="No recent sessions", 
                    bg=LIGHT_BG).pack(pady=20)
        
        # Quick start button
        create_rounded_button(
            dashboard,
            "Start New Learning Session", 
            self.start_new_session,
            bg=PRIMARY_COLOR,
            fg=LIGHT_TEXT,
            radius=20
        ).pack(pady=30, fill="x")
    
    def start_new_session(self):
        """Start a new tutoring session"""
        self.clear_window()
        
        # Header
        header = tk.Frame(self.root, bg=PRIMARY_COLOR, height=80)
        header.pack(fill="x")
        
        tk.Button(
            header,
            text="← Back",
            command=self.show_dashboard,
            bg=PRIMARY_COLOR,
            fg=LIGHT_TEXT,
            bd=0,
            font=("Segoe UI", 10)
        ).pack(side="left", padx=20)
        
        tk.Label(
            header,
            text="New Session",
            font=("Segoe UI", 18, "bold"),
            bg=PRIMARY_COLOR,
            fg=LIGHT_TEXT
        ).pack(side="left", padx=20)
        
        # Subject selection
        content = tk.Frame(self.root, bg=LIGHT_BG)
        content.pack(expand=True, fill="both", padx=100, pady=50)
        
        # Subject selection card
        subject_card = Card(content, title="Select Subject")
        subject_card.pack(fill="both", expand=True)
        
        tk.Label(
            subject_card.content_frame,
            text="Choose a subject to begin:",
            font=("Segoe UI", 10),
            bg=CARD_COLOR,
            fg=DARK_TEXT
        ).pack(pady=10)
        
        self.subject_var = tk.StringVar()
        subjects = ["Mathematics", "Physics", "Chemistry", "Biology", 
                   "Computer Science", "History", "Literature", "English", 
                   "Geography", "Art", "Music", "Physical Education"]
        
        for subject in subjects:
            ModernRadioButton(
                subject_card.content_frame,
                text=subject,
                variable=self.subject_var,
                value=subject,
                command=lambda: None
            ).pack(anchor="w", pady=2, padx=20)
        
        # Start button
        btn_frame = tk.Frame(subject_card.content_frame, bg=CARD_COLOR)
        btn_frame.pack(fill="x", pady=20)
        
        create_rounded_button(
            btn_frame,
            "Start Session",
            self.launch_session,
            bg=PRIMARY_COLOR,
            radius=20
        ).pack(side="left", padx=10)
        
        create_rounded_button(
            btn_frame,
            "Back",
            self.show_dashboard,
            bg=ACCENT_COLOR,
            radius=20
        ).pack(side="left", padx=10)
    
    def launch_session(self):
        """Launch the actual tutoring session"""
        subject = self.subject_var.get()
        if not subject:
            messagebox.showerror("Error", "Please select a subject")
            return
            
        self.current_session = self.engine.start_session(self.current_user.user_id, subject)
        self.show_session_interface()
    
    def show_session_interface(self):
        """Show the main tutoring session interface"""
        self.clear_window()
        
        # Header with session info
        header = tk.Frame(self.root, bg=PRIMARY_COLOR, height=60)
        header.pack(fill="x")
        
        tk.Label(
            header,
            text=f"{self.current_session.subject} Session",
            font=("Segoe UI", 14, "bold"),
            bg=PRIMARY_COLOR,
            fg=LIGHT_TEXT
        ).pack(side="left", padx=20)
        
        create_rounded_button(
            header,
            "End Session",
            self.end_current_session,
            bg=ACCENT_COLOR,
            radius=15
        ).pack(side="right", padx=20)
        
        # Main content area
        main_content = tk.Frame(self.root, bg=LIGHT_BG)
        main_content.pack(expand=True, fill="both", padx=10, pady=10)
        
        # Left panel - Chat interface (70% width)
        chat_frame = tk.Frame(main_content, bg=LIGHT_BG)
        chat_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        # Conversation display in a card
        chat_card = Card(chat_frame, title="Learning Conversation")
        chat_card.pack(fill="both", expand=True)
        
        self.conversation_text = ModernScrolledText(chat_card.content_frame)
        self.conversation_text.pack(fill="both", expand=True, pady=5)
        self.conversation_text.config(state=tk.DISABLED)
        
        # User input area
        input_card = Card(chat_frame)
        input_card.pack(fill="x", pady=(5, 0))
        
        input_frame = tk.Frame(input_card.content_frame, bg=CARD_COLOR)
        input_frame.pack(fill="x", pady=5, padx=5)
        
        self.user_input = ModernEntry(input_frame, placeholder="Type your question here...")
        self.user_input.pack(side="left", fill="x", expand=True, padx=5)
        self.user_input.bind("<Return>", lambda e: self.send_message())
        
        # Input buttons
        btn_frame = tk.Frame(input_frame, bg=CARD_COLOR)
        btn_frame.pack(side="left")
        
        create_rounded_button(
            btn_frame,
            "Send",
            self.send_message,
            bg=PRIMARY_COLOR,
            radius=15
        ).pack(side="left", padx=2)
        
        create_rounded_button(
            btn_frame,
            "🎤",
            self.toggle_voice_input,
            bg=SECONDARY_COLOR,
            radius=15
        ).pack(side="left", padx=2)
        
        # Right panel - Tools (30% width)
        tools_frame = tk.Frame(main_content, bg=LIGHT_BG, width=300)
        tools_frame.pack(side="right", fill="y", padx=5, pady=5)
        
        # Whiteboard card
        wb_card = Card(tools_frame, title="Interactive Whiteboard")
        wb_card.pack(fill="x", pady=(0, 10))
        
        self.whiteboard = ModernWhiteboard(wb_card.content_frame, height=200)
        self.whiteboard.pack(fill="x", pady=5)
        
        # Whiteboard controls
        wb_btn_frame = tk.Frame(wb_card.content_frame, bg=CARD_COLOR)
        wb_btn_frame.pack(fill="x", pady=5)
        
        create_rounded_button(
            wb_btn_frame,
            "Clear",
            self.whiteboard.clear,
            bg=ACCENT_COLOR,
            radius=15
        ).pack(side="left", padx=2)
        
        create_rounded_button(
            wb_btn_frame,
            "Generate",
            self.generate_whiteboard_content,
            bg=PRIMARY_COLOR,
            radius=15
        ).pack(side="left", padx=2)
        
        # Learning objectives card
        obj_card = Card(tools_frame, title="Learning Objectives")
        obj_card.pack(fill="x", pady=(0, 10))
        
        for i, obj in enumerate(self.current_session.learning_objectives, 1):
            tk.Label(
                obj_card.content_frame,
                text=f"• {obj}",
                font=("Segoe UI", 10),
                bg=CARD_COLOR,
                fg=DARK_TEXT,
                wraplength=250,
                justify="left"
            ).pack(anchor="w", padx=5, pady=2)
        
        # Session tools card
        tools_card = Card(tools_frame, title="Session Tools")
        tools_card.pack(fill="x")
        
        tools_btn_frame = tk.Frame(tools_card.content_frame, bg=CARD_COLOR)
        tools_btn_frame.pack(fill="x", pady=5)
        
        create_rounded_button(
            tools_btn_frame,
            "Generate Quiz",
            self.generate_quiz,
            bg=PRIMARY_COLOR,
            radius=15
        ).pack(fill="x", pady=2)
        
        create_rounded_button(
            tools_btn_frame,
            "Suggested Follow-ups",
            self.show_followups,
            bg=SECONDARY_COLOR,
            radius=15
        ).pack(fill="x", pady=2)
        
        # Display welcome message
        self.display_message("AI Tutor", f"Welcome to your {self.current_session.subject} session! How can I help you today?")

    def send_message(self):
        """Send user message to AI tutor"""
        message = self.user_input.get()
        if not message or message == "Type your question here...":
            return
            
        self.display_message("You", message)
        self.user_input.delete(0, tk.END)
        
        # Show typing indicator
        self.conversation_text.config(state=tk.NORMAL)
        self.conversation_text.insert(tk.END, "\nAI Tutor is typing...\n")
        self.conversation_text.see(tk.END)
        self.conversation_text.config(state=tk.DISABLED)
        self.root.update()
        
        # Get AI response in a separate thread
        threading.Thread(target=self.get_ai_response, args=(message,), daemon=True).start()
    
    def get_ai_response(self, message):
        """Get response from AI tutor"""
        try:
            response, followups = self.engine.get_tutoring_response(
                self.current_session.session_id, message
            )
            
            # Remove typing indicator
            self.conversation_text.config(state=tk.NORMAL)
            self.conversation_text.delete("end-2l linestart", "end-1c")
            self.conversation_text.config(state=tk.DISABLED)
            
            self.display_message("AI Tutor", response)
            
            # Speak the response if voice is enabled
            if hasattr(self, 'voice_enabled') and self.voice_enabled:
                self.engine.text_to_speech(response)
                
            # Store followups for later
            self.current_followups = followups
            
        except Exception as e:
            logger.error(f"Error getting AI response: {e}")
            self.display_message("System", f"An error occurred: {str(e)}")
    
    def toggle_voice_input(self):
        """Toggle voice input mode"""
        if hasattr(self, 'voice_enabled') and self.voice_enabled:
            self.voice_enabled = False
            self.stop_voice_event.set()
            messagebox.showinfo("Voice Input", "Voice input disabled")
        else:
            self.voice_enabled = True
            self.stop_voice_event.clear()
            messagebox.showinfo("Voice Input", "Voice input enabled - press and hold the button to speak")
            threading.Thread(target=self.voice_input_loop, daemon=True).start()
    
    def voice_input_loop(self):
        """Continuous voice input loop"""
        while not self.stop_voice_event.is_set():
            try:
                with sr.Microphone() as source:
                    self.engine.voice_recognizer.adjust_for_ambient_noise(source)
                    audio = self.engine.voice_recognizer.listen(source, timeout=3)
                    
                    text = self.engine.voice_recognizer.recognize_google(audio)
                    self.user_input.delete(0, tk.END)
                    self.user_input.insert(0, text)
                    self.send_message()
                    
            except sr.WaitTimeoutError:
                continue
            except Exception as e:
                logger.error(f"Voice input error: {e}")
                continue
    
    def generate_quiz(self):
        """Generate and display a quiz question"""
        difficulty = simpledialog.askstring("Quiz Difficulty", 
                                          "Enter difficulty (easy/medium/hard):",
                                          parent=self.root)
        if not difficulty:
            return
            
        quiz = self.engine.generate_quiz(self.current_session.session_id, difficulty)
        
        # Create quiz window
        quiz_win = tk.Toplevel(self.root)
        quiz_win.title(f"{self.current_session.subject} Quiz")
        quiz_win.geometry("500x400")
        
        # Display question
        tk.Label(quiz_win, text=quiz['question'], 
                font=("Segoe UI", 12), wraplength=400).pack(pady=10)
        
        # Display options
        self.quiz_var = tk.IntVar()
        for i, option in enumerate(quiz['options']):
            rb = tk.Radiobutton(quiz_win, text=option, 
                               variable=self.quiz_var, value=i,
                               font=("Segoe UI", 10))
            rb.pack(anchor="w", padx=20, pady=2)
        
        # Submit button
        create_rounded_button(
            quiz_win,
            "Submit", 
            lambda: self.check_quiz_answer(quiz, quiz_win),
            bg=PRIMARY_COLOR,
            radius=20
        ).pack(pady=10, fill="x", padx=50)
    
    def check_quiz_answer(self, quiz, window):
        """Check if quiz answer is correct"""
        user_answer = self.quiz_var.get()
        
        if user_answer == quiz['correct_answer']:
            result = "✅ Correct!"
            color = "green"
        else:
            result = "❌ Incorrect"
            color = "red"
        
        # Show result
        result_frame = tk.Frame(window)
        result_frame.pack(pady=10)
        
        tk.Label(result_frame, text=result, fg=color, 
                font=("Segoe UI", 12, "bold")).pack()
        tk.Label(result_frame, text="Explanation: " + quiz['explanation'],
                wraplength=400).pack()
        
        # Close button
        create_rounded_button(
            window,
            "Close", 
            window.destroy,
            bg=ACCENT_COLOR,
            radius=20
        ).pack(pady=10, fill="x", padx=50)
    
    def show_followups(self):
        """Show suggested follow-up questions"""
        if not hasattr(self, 'current_followups') or not self.current_followups:
            messagebox.showinfo("Follow-ups", "No follow-up questions available yet. Ask a question first.")
            return
            
        # Create follow-ups window
        follow_win = tk.Toplevel(self.root)
        follow_win.title("Suggested Follow-up Questions")
        follow_win.geometry("500x300")
        
        tk.Label(follow_win, text="Here are some follow-up questions you might ask:",
                font=("Segoe UI", 12)).pack(pady=10)
        
        for i, question in enumerate(self.current_followups, 1):
            frame = tk.Frame(follow_win)
            frame.pack(fill="x", padx=10, pady=2)
            
            tk.Label(frame, text=f"{i}. {question}", 
                    wraplength=400, justify="left").pack(side="left")
            create_rounded_button(
                frame,
                "Ask", 
                lambda q=question: self.ask_followup(q, follow_win),
                bg=PRIMARY_COLOR,
                radius=15
            ).pack(side="right", padx=5)
    
    def ask_followup(self, question, window):
        """Ask a follow-up question"""
        self.user_input.delete(0, tk.END)
        self.user_input.insert(0, question)
        self.send_message()
        window.destroy()
    
    def generate_whiteboard_content(self):
        """Generate content for the whiteboard"""
        concept = simpledialog.askstring("Whiteboard Content", 
                                       "Enter concept to visualize:",
                                       parent=self.root)
        if not concept:
            return
            
        content = self.engine.generate_whiteboard_content(concept)
        
        # Clear and prepare whiteboard
        self.whiteboard.clear()
        
        # Display explanation
        self.display_message("AI Tutor", f"Whiteboard content for: {concept}\n\n{content['explanation']}")
        
        # For demo, just show a simple representation
        colors = content.get('color_scheme', [PRIMARY_COLOR, ACCENT_COLOR, "#4fd1c5"])
        
        # Draw title
        self.whiteboard.create_text(150, 20, text=content['title'], 
                                  fill=colors[0], font=("Segoe UI", 12, "bold"))
        
        # Simple visualization
        if "diagram" in concept.lower():
            # Draw a simple diagram
            self.whiteboard.create_rectangle(50, 50, 250, 150, 
                                           outline=colors[0], width=2)
            self.whiteboard.create_oval(100, 80, 200, 130, 
                                      outline=colors[1], width=2)
            self.whiteboard.create_line(150, 50, 150, 150, 
                                      fill=colors[2], width=2)
        else:
            # Draw a concept map
            self.whiteboard.create_oval(100, 50, 200, 100, 
                                      outline=colors[0], width=2)
            self.whiteboard.create_text(150, 75, text=concept[:10], 
                                      fill=colors[0])
            
            self.whiteboard.create_line(150, 100, 100, 150, 
                                      fill=colors[1], width=2)
            self.whiteboard.create_oval(75, 150, 125, 200, 
                                      outline=colors[1], width=2)
            self.whiteboard.create_text(100, 175, text="Example", 
                                      fill=colors[1])
            
            self.whiteboard.create_line(150, 100, 200, 150, 
                                      fill=colors[2], width=2)
            self.whiteboard.create_rectangle(175, 150, 225, 200, 
                                           outline=colors[2], width=2)
            self.whiteboard.create_text(200, 175, text="Application", 
                                      fill=colors[2])
    
    def end_current_session(self):
        """End the current tutoring session"""
        if not self.current_session:
            return
            
        summary = self.engine.end_session(self.current_session.session_id)
        
        # Show summary
        summary_win = tk.Toplevel(self.root)
        summary_win.title("Session Summary")
        summary_win.geometry("600x500")
        
        tk.Label(summary_win, text=f"Session Summary - {self.current_session.subject}", 
                font=("Segoe UI", 14, "bold")).pack(pady=10)
        
        # Topics covered
        topics_frame = tk.Frame(summary_win)
        topics_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(topics_frame, text="Topics Covered:", 
                font=("Segoe UI", 12, "bold")).pack(anchor="w")
        for topic in summary['topics_covered']:
            tk.Label(topics_frame, text=f"- {topic}", 
                    wraplength=550, justify="left").pack(anchor="w")
        
        # Key learnings
        learnings_frame = tk.Frame(summary_win)
        learnings_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(learnings_frame, text="Key Learnings:", 
                font=("Segoe UI", 12, "bold")).pack(anchor="w")
        for learning in summary['key_learnings']:
            tk.Label(learnings_frame, text=f"- {learning}", 
                    wraplength=550, justify="left").pack(anchor="w")
        
        # Next steps
        steps_frame = tk.Frame(summary_win)
        steps_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(steps_frame, text="Suggested Next Steps:", 
                font=("Segoe UI", 12, "bold")).pack(anchor="w")
        for step in summary['suggested_next_steps']:
            tk.Label(steps_frame, text=f"- {step}", 
                    wraplength=550, justify="left").pack(anchor="w")
        
        # Performance rating
        rating_frame = tk.Frame(summary_win)
        rating_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(rating_frame, text=f"Performance Rating: {summary['performance_rating']}/5", 
                font=("Segoe UI", 12, "bold")).pack(anchor="w")
        
        # Close button
        create_rounded_button(
            summary_win,
            "Back to Dashboard", 
            lambda: [summary_win.destroy(), self.show_dashboard()],
            bg=PRIMARY_COLOR,
            radius=20
        ).pack(pady=10, fill="x", padx=50)
        
        self.current_session = None
    
    def show_session_history(self):
        """Show user's session history"""
        self.clear_window()
        
        # Header
        header = tk.Frame(self.root, bg=PRIMARY_COLOR, height=80)
        header.pack(fill="x")
        
        tk.Button(
            header,
            text="← Back",
            command=self.show_dashboard,
            bg=PRIMARY_COLOR,
            fg=LIGHT_TEXT,
            bd=0,
            font=("Segoe UI", 10)
        ).pack(side="left", padx=20)
        
        tk.Label(
            header,
            text="Session History",
            font=("Segoe UI", 18, "bold"),
            bg=PRIMARY_COLOR,
            fg=LIGHT_TEXT
        ).pack(side="left", padx=20)
        
        # Main content
        content = tk.Frame(self.root, bg=LIGHT_BG)
        content.pack(expand=True, fill="both", padx=20, pady=20)
        
        if not self.current_user.session_history:
            tk.Label(content, text="No session history available", 
                    bg=LIGHT_BG).pack(pady=50)
            return
            
        # Create a treeview for sessions
        columns = ("subject", "date", "duration", "rating")
        tree = ttk.Treeview(content, columns=columns, show="headings")
        
        # Define headings
        tree.heading("subject", text="Subject")
        tree.heading("date", text="Date")
        tree.heading("duration", text="Duration")
        tree.heading("rating", text="Rating")
        
        # Add data
        for session in self.current_user.session_history:
            start = datetime.datetime.fromisoformat(session['start_time'])
            end = datetime.datetime.fromisoformat(session.get('end_time', session['start_time']))
            duration = end - start
            
            tree.insert("", tk.END, 
                        values=(
                            session['subject'],
                            start.strftime("%Y-%m-%d"),
                            str(duration).split(".")[0],
                            session.get('performance_rating', 'N/A')
                        ))
        
        tree.pack(expand=True, fill="both")
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(content, orient="vertical", command=tree.yview)
        scrollbar.pack(side="right", fill="y")
        tree.configure(yscrollcommand=scrollbar.set)
    
    def show_analytics(self):
        """Show learning analytics dashboard"""
        self.clear_window()
        
        # Header
        header = tk.Frame(self.root, bg=PRIMARY_COLOR, height=80)
        header.pack(fill="x")
        
        tk.Button(
            header,
            text="← Back",
            command=self.show_dashboard,
            bg=PRIMARY_COLOR,
            fg=LIGHT_TEXT,
            bd=0,
            font=("Segoe UI", 10)
        ).pack(side="left", padx=20)
        
        tk.Label(
            header,
            text="Learning Analytics",
            font=("Segoe UI", 18, "bold"),
            bg=PRIMARY_COLOR,
            fg=LIGHT_TEXT
        ).pack(side="left", padx=20)
        
        # Main content
        content = tk.Frame(self.root, bg=LIGHT_BG)
        content.pack(expand=True, fill="both", padx=20, pady=20)
        
        if not self.current_user.session_history:
            tk.Label(content, text="No analytics data available", 
                    bg=LIGHT_BG).pack(pady=50)
            return
            
        # Create analytics charts
        notebook = ttk.Notebook(content)
        notebook.pack(expand=True, fill="both")
        
        # Time spent per subject
        time_frame = tk.Frame(notebook, bg=LIGHT_BG)
        notebook.add(time_frame, text="Time by Subject")
        
        # Prepare data
        subject_time = {}
        for session in self.current_user.session_history:
            start = datetime.datetime.fromisoformat(session['start_time'])
            end = datetime.datetime.fromisoformat(session.get('end_time', session['start_time']))
            duration = (end - start).total_seconds() / 60  # in minutes
            
            if session['subject'] in subject_time:
                subject_time[session['subject']] += duration
            else:
                subject_time[session['subject']] = duration
        
        # Create pie chart
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.pie(subject_time.values(), labels=subject_time.keys(), autopct='%1.1f%%')
        ax.set_title("Time Spent by Subject")
        
        canvas = FigureCanvasTkAgg(fig, master=time_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(expand=True, fill="both")
        
        # Performance over time
        perf_frame = tk.Frame(notebook, bg=LIGHT_BG)
        notebook.add(perf_frame, text="Performance Trend")
        
        # Prepare data
        dates = []
        ratings = []
        for session in self.current_user.session_history:
            if 'performance_rating' in session:
                dates.append(datetime.datetime.fromisoformat(session['start_time']))
                ratings.append(session['performance_rating'])
        
        if ratings:
            fig2, ax2 = plt.subplots(figsize=(6, 4))
            ax2.plot(dates, ratings, marker='o')
            ax2.set_title("Performance Over Time")
            ax2.set_ylim(0, 5)
            ax2.set_ylabel("Rating (1-5)")
            
            canvas2 = FigureCanvasTkAgg(fig2, master=perf_frame)
            canvas2.draw()
            canvas2.get_tk_widget().pack(expand=True, fill="both")
        else:
            tk.Label(perf_frame, text="No performance data available", 
                    bg=LIGHT_BG).pack(pady=50)
    
    def show_settings(self):
        """Show user settings"""
        self.clear_window()
        
        # Header
        header = tk.Frame(self.root, bg=PRIMARY_COLOR, height=80)
        header.pack(fill="x")
        
        tk.Button(
            header,
            text="← Back",
            command=self.show_dashboard,
            bg=PRIMARY_COLOR,
            fg=LIGHT_TEXT,
            bd=0,
            font=("Segoe UI", 10)
        ).pack(side="left", padx=20)
        
        tk.Label(
            header,
            text="Settings",
            font=("Segoe UI", 18, "bold"),
            bg=PRIMARY_COLOR,
            fg=LIGHT_TEXT
        ).pack(side="left", padx=20)
        
        # Main content
        content = tk.Frame(self.root, bg=LIGHT_BG)
        content.pack(expand=True, fill="both", padx=50, pady=20)
        
        # User info
        user_card = Card(content, title="User Profile")
        user_card.pack(fill="x", pady=10)
        
        # Avatar
        avatar_frame = tk.Frame(user_card.content_frame, bg=CARD_COLOR)
        avatar_frame.pack(pady=5)
        
        if hasattr(self.current_user, 'avatar_path') and self.current_user.avatar_path:
            try:
                img = Image.open(self.current_user.avatar_path)
                img = img.resize((100, 100), Image.Resampling.LANCZOS)
                self.avatar_img = ImageTk.PhotoImage(img)
                tk.Label(avatar_frame, image=self.avatar_img, bg=CARD_COLOR).pack(side="left", padx=10)
            except Exception as e:
                logger.error(f"Error loading avatar: {e}")
                tk.Label(avatar_frame, text="No Avatar", bg=CARD_COLOR).pack(side="left", padx=10)
        else:
            tk.Label(avatar_frame, text="No Avatar", bg=CARD_COLOR).pack(side="left", padx=10)
        
        create_rounded_button(
            avatar_frame,
            "Change Avatar",
            self.change_avatar,
            bg=SECONDARY_COLOR,
            radius=15
        ).pack(side="left", padx=10)
        
        # User details
        details_frame = tk.Frame(user_card.content_frame, bg=CARD_COLOR)
        details_frame.pack(fill="x", pady=5)
        
        tk.Label(details_frame, text=f"Name: {self.current_user.name}", 
                bg=CARD_COLOR).pack(anchor="w", padx=10, pady=2)
        tk.Label(details_frame, text=f"Learning Style: {self.current_user.learning_style}", 
                bg=CARD_COLOR).pack(anchor="w", padx=10, pady=2)
        tk.Label(details_frame, text=f"Proficiency Level: {self.current_user.proficiency_level}", 
                bg=CARD_COLOR).pack(anchor="w", padx=10, pady=2)
        
        # Preferences
        pref_card = Card(content, title="Preferences")
        pref_card.pack(fill="x", pady=10)
        
        # Voice settings
        voice_frame = tk.Frame(pref_card.content_frame, bg=CARD_COLOR)
        voice_frame.pack(fill="x", pady=5)
        
        self.voice_var = tk.BooleanVar(value=hasattr(self, 'voice_enabled') and self.voice_enabled)
        tk.Checkbutton(voice_frame, text="Enable Voice Interaction", 
                      variable=self.voice_var, bg=CARD_COLOR).pack(anchor="w", padx=10)
        
        # Save button
        create_rounded_button(
            content,
            "Save Settings",
            self.save_settings,
            bg=PRIMARY_COLOR,
            radius=20
        ).pack(pady=20, fill="x")
    
    def change_avatar(self):
        """Change user avatar image"""
        file_path = filedialog.askopenfilename(
            title="Select Avatar Image",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg")]
        )
        
        if file_path:
            try:
                # Store the path in user profile
                self.current_user.avatar_path = file_path
                
                # Update in engine
                self.engine.user_profiles[self.current_user.user_id] = self.current_user
                self.engine.save_user_data()
                
                # Refresh settings view
                self.show_settings()
            except Exception as e:
                messagebox.showerror("Error", f"Could not set avatar: {str(e)}")
    
    def save_settings(self):
        """Save user settings"""
        try:
            # Update voice setting
            self.voice_enabled = self.voice_var.get()
            
            # Save to engine
            self.engine.user_profiles[self.current_user.user_id] = self.current_user
            self.engine.save_user_data()
            
            messagebox.showinfo("Success", "Settings saved successfully")
            self.show_dashboard()
        except Exception as e:
            messagebox.showerror("Error", f"Could not save settings: {str(e)}")
    
    def display_message(self, sender: str, message: str):
        """Display a message in the conversation window"""
        self.conversation_text.config(state=tk.NORMAL)
        
        # Configure tags for different senders
        if sender == "You":
            color = PRIMARY_COLOR
        elif sender == "AI Tutor":
            color = SECONDARY_COLOR
        else:
            color = DARK_TEXT
        
        # Insert sender with appropriate styling
        self.conversation_text.tag_config(sender, foreground=color, font=("Segoe UI", 10, "bold"))
        self.conversation_text.insert(tk.END, f"{sender}: ", sender)
        
        # Insert message
        self.conversation_text.insert(tk.END, f"{message}\n")
        
        self.conversation_text.see(tk.END)
        self.conversation_text.config(state=tk.DISABLED)
    
    def clear_window(self):
        """Clear all widgets from the window"""
        for widget in self.root.winfo_children():
            widget.destroy()

def main():
    # Initialize components
    knowledge_base = LocalKnowledgeBase()
    
    # Get API key from user
    root = tk.Tk()
    root.withdraw()  # Hide the temporary window
    api_key = simpledialog.askstring("API Key", "Enter your OpenAI API key:", show='*')
    
    if not api_key:
        messagebox.showerror("Error", "API key is required")
        return

    # Initialize engine
    engine = TutoringEngine(api_key=api_key, knowledge_base=knowledge_base)
    
    # Create and configure main window
    root.deiconify()  # Make visible
    root.title("EduMentor AI")
    root.geometry("1200x800")
    
    # Force window focus (critical fix)
    root.after(100, lambda: root.focus_force())
    
    # Start the application
    app = ModernTutoringApp(root, engine)
    root.mainloop()

if __name__ == "__main__":
    main()