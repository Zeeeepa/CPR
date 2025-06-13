# CPR (Codegen PR) - AI Agent Chat Interface

A modern, real-time chat interface for interacting with Codegen AI agents. Built with Nuxt 3, Vue 3, and FastAPI.

## 🚀 Features

- **Real-time Chat Interface**: Interactive chat with AI agents
- **Dynamic Progress Tracking**: Live updates on task execution steps
- **Connection Status Monitoring**: Real-time connection status indicators
- **Thread Management**: Create and manage multiple conversation threads
- **Modern UI**: Dark theme with Tailwind CSS and Heroicons
- **API Integration**: Full integration with Codegen SDK
- **Enhanced Agent State Retrieval**: Properly retrieves and displays agent state and responses
- **Robust Error Handling**: Comprehensive error handling and recovery mechanisms
- **Improved Streaming**: Better SSE streaming implementation for real-time updates

## 🏗️ Architecture

- **Frontend**: Nuxt 3 + Vue 3 + TypeScript + Tailwind CSS
- **Backend**: FastAPI + Python + Codegen SDK
- **Real-time Updates**: Server-Sent Events (SSE) for live progress
- **State Management**: Vue 3 Composition API with reactive state

## 📋 Prerequisites

- Node.js 18+ and npm
- Python 3.8+ and pip
- Codegen API credentials (token and org ID)

## 🛠️ Setup

### 1. Clone and Install Dependencies

```bash
# Install frontend dependencies
npm install

# Install backend dependencies
cd backend && pip install -r requirements.txt && cd ..
```

### 2. Environment Configuration

Copy the environment template and add your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your actual Codegen credentials:

```env
CODEGEN_TOKEN=sk-your-actual-token
CODEGEN_ORG_ID=your-actual-org-id
```

### 3. Validation (Recommended)

Run the comprehensive validation script to ensure everything is set up correctly:

```bash
python validate_ui.py
```

This will validate:
- ✅ Environment setup
- ✅ Frontend build process
- ✅ Backend API structure
- ✅ UI components
- ✅ Configuration files
- ✅ Styling setup
- ✅ Agent state retrieval
- ✅ SSE streaming functionality

## 🚀 Quick Start

### Option 1: Use the Deployment Script (Recommended)

```bash
./deploy.sh
```

This will:
- Install all dependencies
- Validate the environment and setup
- Start the backend API on port 8002
- Start the frontend on port 3001
- Display access URLs

### Option 2: Manual Start

Start the backend API:

```bash
cd backend
uvicorn api:app --host 0.0.0.0 --port 8002 --reload
```

In a new terminal, start the frontend:

```bash
npm run dev
```

## 🌐 Access Points

- **Frontend**: http://localhost:3001
- **Backend API**: http://localhost:8002
- **API Documentation**: http://localhost:8002/docs

## 🧪 Testing

### UI Validation
```bash
python validate_ui.py
```

### Streaming Test
```bash
python test_request.py
```

### Manual Testing Checklist

1. **Connection Test**: Verify connection status shows "Connected" with valid credentials
2. **Thread Creation**: Create new threads and verify they appear in sidebar
3. **Message Flow**: Send messages and verify real-time progress updates
4. **Error Handling**: Test with invalid credentials to verify error states
5. **UI Responsiveness**: Test on different screen sizes
6. **Agent State**: Verify that agent state is properly retrieved and displayed
7. **Response Display**: Check that agent responses are correctly formatted and displayed

## 📁 Project Structure

```
├── components/           # Vue components
│   ├── ChatMessage.vue  # Chat message display
│   └── SettingsModal.vue # Settings configuration
├── pages/
│   └── index.vue        # Main chat interface
├── backend/
│   ├── api.py          # FastAPI backend server
│   └── requirements.txt # Python dependencies
├── assets/             # CSS and static assets
├── public/             # Public static files
├── .env.example        # Environment template
├── validate_ui.py      # UI validation script
├── test_request.py     # Streaming test script
└── deploy.sh          # Deployment script
```

## 🔧 Development

### Frontend Development

```bash
npm run dev          # Start development server
npm run build        # Build for production
npm run preview      # Preview production build
```

### Backend Development

```bash
cd backend
uvicorn api:app --reload  # Start with auto-reload
```

### Code Quality

The project includes:
- TypeScript for type safety
- ESLint for code linting
- Prettier for code formatting
- Tailwind CSS for consistent styling

## 🐛 Troubleshooting

### Common Issues

1. **Connection Failed**: Check your CODEGEN_TOKEN and CODEGEN_ORG_ID in .env
2. **Port Conflicts**: Ensure ports 3001 and 8002 are available
3. **Build Errors**: Run `npm install` to ensure all dependencies are installed
4. **Backend Errors**: Check that Python dependencies are installed with `pip install -r backend/requirements.txt`
5. **Agent State Issues**: If agent state is not being retrieved properly, check the backend logs for errors

### Debug Mode

Start the backend with debug logging:

```bash
cd backend
LOG_LEVEL=debug uvicorn api:app --reload
```

## 📚 API Documentation

The backend provides a comprehensive API with the following endpoints:

- `POST /api/v1/run-task` - Execute AI agent tasks
- `POST /api/v1/test-connection` - Test API connection
- `GET /api/v1/tasks` - List active tasks
- `GET /api/v1/task/{task_id}/status` - Get task status
- `GET /api/v1/task/{task_id}/stream` - Stream task updates
- `GET /docs` - Interactive API documentation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Run validation tests: `python validate_ui.py`
4. Submit a pull request

## 📄 License

This project is part of the Codegen ecosystem. See the main Codegen repository for license information.

## 🆘 Support

For issues and support:
1. Check the troubleshooting section above
2. Run the validation script: `python validate_ui.py`
3. Check the API documentation at http://localhost:8002/docs
4. Review the VALIDATION_CHECKLIST.md for detailed testing steps

