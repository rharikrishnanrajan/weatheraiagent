import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { ChatPage } from './pages/ChatPage';
import { WeatherPage } from './pages/WeatherPage';
import { ProfilePage } from './pages/ProfilePage';
import { KnowledgeBasePage } from './pages/KnowledgeBasePage';

export function App() {
  return (
    <Router>
      <div className="min-h-screen bg-stone-50 flex flex-col font-sans text-stone-900">
        <Navbar />
        <div className="flex-1">
          <Routes>
            <Route path="/" element={<ChatPage />} />
            <Route path="/weather" element={<WeatherPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/kb" element={<KnowledgeBasePage />} />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;
