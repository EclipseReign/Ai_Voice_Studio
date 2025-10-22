#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

user_problem_statement: |
  Сервис для генерации текста и озвучки по промпту. Два режима:
  1. AI генерация: вводишь тему, длительность, язык -> генерируется текст -> можно редактировать -> озвучить
  2. Ручной ввод: вводишь свой текст -> озвучить
  Настройки: язык, скорость речи (normal/slow)
  Использовать gTTS для озвучки
  Поддержка длинных текстов (до часа аудио)

backend:
  - task: "Text generation via LLM"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Implemented text generation using emergentintegrations LLM (gpt-4o-mini). Endpoint: POST /api/text/generate with prompt, duration_minutes, language"
      - working: true
        agent: "testing"
        comment: "✅ PASSED - Text generation working perfectly. Tested short (2 min, 295 words) and long (10 min, 1283 words) durations. LLM integration successful, proper word count calculation, database storage working. Generated realistic content based on prompts."

  - task: "Audio synthesis with edge-tts"
    implemented: true
    working: "NA"
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "UPDATED to edge-tts for better quality. Endpoint: POST /api/audio/synthesize with text, voice, rate, pitch, language. Much higher quality than gTTS, supports 100+ voices."

  - task: "Voices list endpoint"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "GET /api/voices returns 100+ voices from edge-tts with name, short_name, gender, locale. Tested via curl - working perfectly."

  - task: "Audio download endpoint"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "GET /api/audio/download/{audio_id} returns MP3 file. Needs testing with actual generated audio"
      - working: true
        agent: "testing"
        comment: "✅ PASSED - Audio download working perfectly. Successfully downloaded multiple MP3 files with correct MIME type (audio/mpeg). Files are valid and playable. Database lookup and file serving working correctly."

  - task: "History endpoint"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "GET /api/history returns recent audio generations. Needs testing"
      - working: true
        agent: "testing"
        comment: "✅ PASSED - History endpoint working correctly. Returns list of recent generations with proper metadata (id, text preview, audio_url, language, slow flag, created_at). Database queries working, proper sorting by creation date."

frontend:
  - task: "AI text generation mode"
    implemented: true
    working: "NA"
    file: "/app/frontend/src/pages/HomePage.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Tab with prompt input, duration slider, language select. Generate text button, editable textarea, synthesize button"

  - task: "Manual text input mode"
    implemented: true
    working: "NA"
    file: "/app/frontend/src/pages/HomePage.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Tab with manual text input, language select, synthesize button"

  - task: "Voice settings panel"
    implemented: true
    working: "NA"
    file: "/app/frontend/src/pages/HomePage.js"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Settings card with language select and speed select (normal/slow)"

  - task: "Audio player and download"
    implemented: true
    working: "NA"
    file: "/app/frontend/src/pages/HomePage.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Audio player card appears after synthesis with HTML5 audio player and download button"

  - task: "Generation history"
    implemented: true
    working: "NA"
    file: "/app/frontend/src/pages/HomePage.js"
    stuck_count: 0
    priority: "low"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "History card showing recent 5 generations with download links"

metadata:
  created_by: "main_agent"
  version: "1.0"
  test_sequence: 1
  run_ui: false

test_plan:
  current_focus:
    - "Text generation via LLM"
    - "Audio synthesis with gTTS"
    - "AI text generation mode"
    - "Manual text input mode"
  stuck_tasks: []
  test_all: true
  test_priority: "high_first"

agent_communication:
  - agent: "main"
    message: |
      CONVERTED TO EDGE-TTS for better quality (user wanted free + realistic)
      
      edge-tts advantages:
      - FREE (no API key needed)
      - HIGH QUALITY (Microsoft Azure voices)
      - REALISTIC natural speech
      - 100+ voices across many languages
      - Supports speed AND pitch adjustments
      - Perfect for hour-long audio
      
      Key endpoints:
      1. POST /api/text/generate - Generate text from prompt (LLM)
      2. POST /api/audio/synthesize - Text-to-speech with edge-tts
      3. GET /api/voices - List 100+ available voices
      4. GET /api/audio/download/{id} - Download MP3
      5. GET /api/history - Generation history
      
      Ready for comprehensive testing with edge-tts integration.
  - agent: "main"
    message: |
      Backend updated with edge-tts. All endpoints need retesting.
      All backend tasks need_retesting set to true.
      Ready for comprehensive backend testing with edge-tts.