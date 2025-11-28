backend/requirements.txt
```
fastapi
uvicorn
pydantic
```

backend/requirements-dev.txt
```
pytest
requests
flake8
```

backend/tests/test_main.py
```python
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_list_scenarios_empty():
    r = client.get("/scenarios")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert r.json() == []
```

frontend/package.json
```json
{
  "name": "cew-training-frontend",
  "version": "0.1.0",
  "private": true,
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-scripts": "5.0.1",
    "axios": "^1.4.0"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test --watchAll=false"
  }
}
```

frontend/src/index.js
```javascript
import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';

const container = document.getElementById('root') || document.createElement('div');
container.id = 'root';
document.body.appendChild(container);

const root = createRoot(container);
root.render(<App />);
```

frontend/src/App.js
```javascript
import React from 'react';

export default function App() {
  return (
    <div>
      <h1>CEW Training Platform</h1>
      <p>Frontend placeholder.</p>
    </div>
  );
}
```
