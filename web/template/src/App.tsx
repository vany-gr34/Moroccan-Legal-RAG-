import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import HomeView from './components/HomeView';
import ResultsView from './components/ResultsView';
import ArticleOverlay from './components/ArticleOverlay';
import KnowledgeBaseView from './components/KnowledgeBaseView';
import HistoryView from './components/HistoryView';
import { Language, ViewState, QueryResult, SourceArticle } from './types';

// Mock function for simulating a search results
const simulateSearch = (query: string, domain: string): QueryResult => {
  return {
    query,
    domain,
    answerLegal: `يعاقب على تجاوز السرعة القصوى المسموح بها في المدار الحضري بغرامة مالية تتراوح بين 300 و500 درهم، وذلك حسب المادة 172 من مدونة السير، وفي حالة العود تضاعف العقوبة لتصل إلى أقصاها.`,
    answerSimple: `هذا يعني أنه إذا تجاوزت السرعة داخل المدينة وتجاوزت الحد المسموح به، فستتعرض لغرامة مالية تتراوح بين 300 و500 درهم.`,
    sources: [
      {
        id: '1',
        title: 'المادة 172 من مدونة السير',
        law: 'القانون رقم 52.05',
        relevance: 94,
        snippet: 'تجاوز السرعة القصوى المسموح بها في المدار الحضري يعرض المخالف لعقوبة مالية تتراوح بين 300 و500 درهم.',
        content: `تجاوز السرعة القصوى المسموح بها في المدار الحضري يعرض المخالف لعقوبة مالية تتراوح بين 300 و500 درهم. ويعاقب العود بأقصى العقوبة. وكل مخالفة يتم ضبطها بواسطة أجهزة المراقبة الآلية تعتبر ثابتة.`
      },
      {
        id: '2',
        title: 'المادة 173 من مدونة السير',
        law: 'القانون رقم 52.05',
        relevance: 82,
        snippet: 'تجاوز السرعة خارج المدار الحضري...',
        content: 'يعاقب على تجاوز السرعة خارج المدار الحضري بغرامات مختلفة تحدد حسب نسبة التجاوز...'
      },
      {
        id: '3',
        title: 'المادة 180 من مدونة السير',
        law: 'القانون رقم 52.05',
        relevance: 71,
        snippet: 'عدم احترام إشارات المرور...',
        content: 'تبين المواد اللاحقة كيف يتم احتساب نقاط المخالفة...'
      }
    ]
  };
};

export default function App() {
  const [language, setLanguage] = useState<Language>('ar');
  const [currentView, setCurrentView] = useState<ViewState>('home');
  const [queryResult, setQueryResult] = useState<QueryResult | null>(null);
  const [selectedArticle, setSelectedArticle] = useState<SourceArticle | null>(null);

  // Sync RTL direction
  useEffect(() => {
    document.documentElement.dir = language === 'ar' ? 'rtl' : 'ltr';
    document.documentElement.lang = language;
  }, [language]);

  const handleSearch = (query: string, domain: string) => {
    // In a real app, this would be an async API call
    const result = simulateSearch(query, domain);
    setQueryResult(result);
    setCurrentView('results');
  };

  const renderView = () => {
    switch (currentView) {
      case 'home':
        return <HomeView language={language} onSearch={handleSearch} />;
      case 'results':
        return queryResult ? (
          <ResultsView 
            language={language}
            result={queryResult}
            onSourceClick={setSelectedArticle}
            onBack={() => setCurrentView('home')}
          />
        ) : <HomeView language={language} onSearch={handleSearch} />;
      case 'knowledge_base':
        return <KnowledgeBaseView language={language} />;
      case 'history':
        return <HistoryView language={language} />;
      default:
        return <HomeView language={language} onSearch={handleSearch} />;
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-sandstone text-primary transition-colors duration-200">
      <Navbar 
        language={language} 
        setLanguage={setLanguage} 
        currentView={currentView}
        setView={setCurrentView}
      />
      
      <main className="flex-1 flex flex-col relative overflow-hidden">
        {renderView()}
      </main>

      {selectedArticle && (
        <ArticleOverlay 
          language={language} 
          article={selectedArticle} 
          onClose={() => setSelectedArticle(null)} 
        />
      )}
    </div>
  );
}
