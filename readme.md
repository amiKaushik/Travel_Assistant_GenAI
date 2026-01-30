# AI Travel Assistant Bot

## Overview

The **AI Travel Assistant Bot** is an intelligent, web-based travel planning system built using a **pre-trained Gemini-2.5-Flash-Lite Large Language Model (LLM)**. The assistant helps users plan trips based on their **starting location, destination, travel date, and available budget**. It generates multiple realistic travel routes that fit within the given budget and provides detailed travel information in a structured manner.

In addition to route planning, the application also includes a **travel-focused chatbot** that answers user queries strictly related to travel, transportation, and trip planning.

---

## Key Features

* Uses a **pre-trained LLM** (no model training or datasets required)
* Accepts user inputs:

  * Starting place
  * Destination place
  * Available budget
  * Travel date
* Suggests **multiple affordable travel modes**, including:

  * Bus
  * Train
  * Flight
  * Boat (when geographically applicable)
  * Private car / cab
* Displays for each travel option:

  * Available vehicles
  * Departure time
  * Arrival time
  * Total travel time
  * Estimated cost (within budget)
* Generates **realistic, budget-aware travel plans**
* Includes a **travel-only chatbot** for user assistance
* Deployed as an interactive web application using **Streamlit**

---

## System Architecture

The Travel Assistant Bot is divided into four major components:

### Part 1: LLM Model

* Utilizes the **Gemini-2.5-Flash-Lite** pre-trained Large Language Model
* Responsible for reasoning, route comparison, cost estimation, and natural language understanding
* No fine-tuning or custom training is performed

### Part 2: Prompt Engineering

* Carefully designed system and user prompts ensure:

  * Structured JSON output
  * Budget filtering
  * Mandatory travel time inclusion
  * Multiple realistic routes
  * Error handling for invalid inputs
* Prompts strictly restrict the model to travel-related responses only

### Part 3: Memory (Chat History)

* Maintains conversational context during the session
* Stores previous travel-related questions and responses
* Enables a more natural and continuous chatbot experience

### Part 4: Deployment (Streamlit)

* Streamlit is used to build the user interface and deploy the application
* Provides input fields for travel details
* Displays structured travel plans and chatbot responses
* Allows easy local and cloud deployment

---

## Workflow

1. User enters source, destination, budget, and date
2. Inputs are validated
3. Prompt is dynamically generated
4. Prompt is sent to the Gemini LLM
5. LLM reasons and generates affordable travel routes
6. Output is returned in structured JSON format
7. Results are rendered in the Streamlit interface

---

## Tech Stack

* **Programming Language**: Python
* **LLM**: Gemini-2.5-Flash-Lite (Pre-trained)
* **Framework**: Streamlit
* **Prompt Handling**: Prompt Engineering
* **Memory Management**: Session-based chat history
* **Environment**: Virtual Environment (venv)
* **API Integration**: Google Generative AI SDK

---

## Advantages

* No datasets or data files required
* No model training or fine-tuning
* Fast, scalable, and flexible architecture
* Demonstrates real-world LLM usage
* Clean separation of logic, prompts, memory, and UI

---

## Limitations

* Cost and time estimates are approximate (not real-time)
* Depends on LLM reasoning accuracy
* Requires internet connectivity for API access

---

## Future Enhancements

* Integration with real-time travel APIs
* Multi-city and round-trip planning
* Voice-based input
* Cost comparison charts
* Persistent long-term memory

---

👤 Author

Amit Das
|Python | SQL | AI & ML Enthusiast
🚀 Connect With Me
📧 Email: 13amitdas07@gmail.com

kousick Das
|Python | SQL | AI & ML Enthusiast
🚀 Connect With Me
📧 Email: 


Arpan Patra
|Python | SQL | AI & ML Enthusiast
🚀 Connect With Me
📧 Email: arpanpatra800188500@gmail.com


Harshit Kumar Rai
|Python | SQL | AI & ML Enthusiast
🚀 Connect With Me
📧 Email:Raih44531@gmail.com



⭐ Acknowledgement

Thanks to open-source datasets and libraries that made this project possible.


🐙 GitHub: https://github.com/amiKaushik/Travel_Assistant_GenAI
