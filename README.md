# CPR - Codegen PR

A chat interface for interacting with Codegen AI agents.

## Features

- Real-time chat interface with Codegen AI agents
- Streaming responses with progress indicators
- Settings management for API credentials
- Mock mode for testing without actual Codegen API credentials
- Responsive design for desktop and mobile

## Architecture

- **Frontend**: Nuxt 3 + Vue 3 application
- **Backend**: FastAPI Python server
- **Integration**: Codegen SDK for AI agent interactions

## Prerequisites

- Node.js 18+ and npm
- Python 3.9+
- Codegen API credentials (organization ID and token)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Zeeeepa/CPR.git
   cd CPR
   ```

2. Install frontend dependencies:
   ```bash
   npm install
   ```

3. Install backend dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   cd ..
   ```

4. Set up environment variables:
   ```bash
   export CODEGEN_ORG_ID=your_organization_id
   export CODEGEN_TOKEN=your_api_token
   ```

## Running the Application

### Using the Deployment Script

The easiest way to run the application is using the deployment script:

```bash
./deploy.sh
```

This will:
1. Check environment variables
2. Start the backend server
3. Start the frontend server
4. Run validation tests
5. Display URLs for accessing the application

### Manual Startup

If you prefer to start the servers manually:

1. Start the backend server:
   ```bash
   cd backend
   python -m uvicorn api:app --host 0.0.0.0 --port 8002
   ```

2. In a separate terminal, start the frontend server:
   ```bash
   npm run dev
   ```

3. Access the application at:
   - Frontend: http://localhost:3002
   - Backend API: http://localhost:8002

## Testing

Run the validation script to verify that everything is working correctly:

```bash
python validate_ui.py
```

For testing the backend API directly:

```bash
python test_request.py
```

## Mock Mode

The application supports a mock mode for testing without actual Codegen API credentials. This is enabled by default in the backend server.

To disable mock mode and use real Codegen API credentials, set `MOCK_MODE = False` in `backend/api.py`.

## Stopping the Application

To stop all running servers:

```bash
./stop.sh
```

## API Endpoints

- `POST /api/v1/run-task`: Run a task with the Codegen API
- `GET /api/v1/task/{task_id}/stream`: Stream task updates
- `GET /api/v1/task/{task_id}/status`: Get task status
- `POST /api/v1/test-connection`: Test connection to the Codegen API
- `GET /api/v1/config`: Get current configuration
- `GET /api/v1/tasks`: List all active tasks

## License

MIT

