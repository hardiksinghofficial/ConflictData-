import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Dashboard from './Dashboard';
import AnalyticsPage from './components/AnalyticsPage';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/sitrep" element={<AnalyticsPage />} />
      </Routes>
    </Router>
  );
}

export default App;
