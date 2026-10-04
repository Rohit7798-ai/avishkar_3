import React from 'react';
import { BrowserRouter } from 'react-router-dom';
import { AppRoutes } from './routes';
import { TutorialProvider } from './context/TutorialContext';

export default function App() {
  return (
    <BrowserRouter>
      <TutorialProvider>
        <AppRoutes />
      </TutorialProvider>
    </BrowserRouter>
  );
}
