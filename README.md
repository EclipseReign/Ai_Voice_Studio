# AI-Powered Content Creation Platform 🎬

This project is a comprehensive platform designed to streamline the creation of engaging content, leveraging AI to generate text, audio, and video. It offers features like automated hook generation for social media, text-to-speech synthesis, and video creation from images and audio. The platform aims to empower users to produce high-quality content quickly and efficiently. It solves the problem of time-consuming content creation by automating various aspects of the process, from idea generation to final video production.

## 🚀 Key Features

- **User Authentication & Authorization:** Secure user management with Google OAuth integration and session management.
- **Subscription Management:** Handles user subscriptions with free and pro tiers, integrated with PayPal for payments and webhook verification.
- **AI-Powered Hook Generation:** Generates attention-grabbing hooks for social media content using LLMs.
- **Text Generation:** Leverages LLMs to generate creative and engaging text content.
- **Text-to-Speech (TTS):** Synthesizes high-quality audio from text using PiperVoice.
- **Video Generation:** Creates videos from images, audio, and text, supporting various formats like YouTube and Shorts.
- **Cloud Storage Integration:** Utilizes Cloudflare R2 for storing and managing media files.
- **Internationalization (i18n):** Supports multiple languages for a global user base.
- **Multi-Step Video Creation Wizard:** Guides users through the video creation process with an intuitive interface.

## 🛠️ Tech Stack

*   **Frontend:**
    *   React
    *   React Router DOM
    *   i18next
    *   clsx
    *   tailwind-merge
    *   lucide-react
    *   axios
*   **Backend:**
    *   FastAPI
    *   Motor (Async MongoDB Driver)
    *   GridFS
    *   aiohttp
    *   requests
    *   PiperVoice
    *   emergentintegrations.llm.chat
*   **Database:**
    *   MongoDB
*   **AI Tools:**
    *   Large Language Models (LLMs) - e.g., GPT-3.5-turbo
    *   Pollinations AI (for image generation)
    *   Piper (for text-to-speech)
    *   faster-whisper (optional, for subtitle timing)
*   **Payment Integration:**
    *   PayPal
*   **Cloud Storage:**
    *   Cloudflare R2
*   **Build Tools:**
    *   Create React App (CRA)
    *   Craco (CRA Configuration Override)
    *   Webpack
    *   Babel
*   **Other:**
    *   Python
    *   Node.js
    *   dotenv
    *   os
    *   logging
    *   uuid
    *   datetime
    *   timezone
    *   timedelta
    *   typing
    *   email
    *   hmac
    *   hashlib
    *   urllib
    *   json
    *   wave
    *   pydub
    *   re
    *   struct
    *   concurrent.futures
    *   multiprocessing
    *   psutil
    *   time
    *   gc

## 📦 Getting Started / Setup Instructions

### Prerequisites

*   Node.js and npm (or yarn) for frontend development.
*   Python 3.7+ for backend development.
*   MongoDB installed and running.
*   Cloudflare R2 bucket configured.
*   PayPal developer account for API credentials.
*   Environment variables configured (see `.env.example` files in `frontend` and `backend` directories).

### Installation

**Backend:**

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Frontend:**

```bash
cd frontend
npm install # or yarn install
```

### Running Locally

**Backend:**

1.  Set the environment variables in a `.env` file based on `.env.example`.
2.  Run the FastAPI server:

```bash
cd backend
uvicorn server:app --reload
```

**Frontend:**

1.  Set the environment variables in a `.env` file based on `.env.example`.  Make sure `REACT_APP_BACKEND_URL` points to your running backend.
2.  Start the React development server:

```bash
cd frontend
npm start # or yarn start
```

## 💻 Project Structure

```
📂 project-root
├── backend/
│   ├── __init__.py
│   ├── auth.py          # Handles user authentication
│   ├── models.py        # Data models (User, Subscription, etc.)
│   ├── r2_service.py    # Cloudflare R2 service
│   ├── server.py        # Main FastAPI application
│   ├── subscription.py  # Subscription management logic
│   ├── viral_hooks.py   # AI hook generation
│   ├── video_service.py # Video generation service
│   ├── venv/            # Python virtual environment
│   └── requirements.txt # Python dependencies
├── frontend/
│   ├── public/          # Static assets
│   ├── src/
│   │   ├── App.js       # Main application component
│   │   ├── App.css      # Global CSS styles
│   │   ├── index.js     # Entry point for React application
│   │   ├── index.css    # Global CSS styles
│   │   ├── i18n.js      # Internationalization configuration
│   │   ├── contexts/    # React Contexts (Auth, Theme)
│   │   ├── components/  # Reusable React components
│   │   ├── pages/       # Page-level components
│   │   ├── lib/         # Utility functions
│   │   └── ...
│   ├── craco.config.js  # CRA configuration override
│   ├── package.json     # Frontend dependencies
│   └── ...
├── README.md          # This file
└── ...
```

## 📸 Screenshots

(Space for screenshots of the application in action)

## 🤝 Contributing

We welcome contributions to this project! Please follow these steps:

1.  Fork the repository.
2.  Create a new branch for your feature or bug fix.
3.  Make your changes and commit them with clear, concise messages.
4.  Submit a pull request.

## 📝 License

This project is licensed under the [MIT License](LICENSE).

## 📬 Contact

For questions or inquiries, please contact: [Your Name/Organization] at [Your Email].

## 💖 Thanks Message

Thank you for checking out our project! We hope you find it useful and we appreciate any feedback or contributions.

This is written by [readme.ai](https://readme-generator-phi.vercel.app/), your go-to platform for generating beautiful and informative README files.
