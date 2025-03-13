// src/index.tsx
import App from './App';
import React from 'react';
import ReactDOM from 'react-dom/client';
import reportWebVitals from './reportWebVitals';

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// 如果你想开始测量应用的性能，请将函数传递给reportWebVitals
// reportWebVitals(console.log);
// 详细了解: https://bit.ly/CRA-vitals
reportWebVitals();