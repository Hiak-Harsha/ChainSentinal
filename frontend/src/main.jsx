import React, { useState } from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';
import LandingSequence from './components/landing/LandingSequence.jsx';
import './index.css';

function Root() {
  const [showApp, setShowApp] = useState(
    () => sessionStorage.getItem('cs_intro_seen') === 'true'
  );

  return showApp ? (
    <App />
  ) : (
    <LandingSequence
      onComplete={() => {
        sessionStorage.setItem('cs_intro_seen', 'true');
        setShowApp(true);
      }}
    />
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>
);
