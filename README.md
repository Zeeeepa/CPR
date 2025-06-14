# CPR - Codegen PR Reviewer

A simple application for managing threads and messages with Codegen AI.

## Setup

1. Clone the repository
2. Create a `.env` file with your Codegen API credentials:
   ```
   CODEGEN_ORG_ID=your_org_id
   CODEGEN_TOKEN=your_token
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Running the Application

Start the backend server:

```bash
python -m uvicorn backend.api:app --host 0.0.0.0 --port 8002 --reload
```

## Running Tests

All tests are located in the `tests` directory. To run all tests:

```bash
cd tests
./run_all_tests.sh
```

Or to start the backend server and run tests in one command:

```bash
cd tests
./start_and_test.sh
```

## API Documentation

Once the server is running, you can access the API documentation at:
http://localhost:8002/docs

