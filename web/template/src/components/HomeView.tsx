import React, { useState } from 'react';
import { Search, UploadCloud } from 'lucide-react';
import { Language, QueryResult } from '../types';
import { getTranslation } from '../i18n';

interface HomeViewProps {
  language: Language;
  onSearch: (query: string, domain: string) => void;
}

export default function HomeView({ language, onSearch }: HomeViewProps) {
  const t = (key: Parameters<typeof getTranslation>[1]) => getTranslation(language, key);
  const isRTL = language === 'ar';
  
  const [query, setQuery] = useState('');
  const [domain, setDomain] = useState('all');

  const domains = [
    { id: 'all', label: t('allDomains') },
    { id: 'criminal', label: t('domainCriminal') },
    { id: 'traffic', label: t('domainTraffic') },
    { id: 'family', label: t('domainFamily') },
    { id: 'civil', label: t('domainCivil') },
    { id: 'commercial', label: t('domainCommercial') },
    { id: 'procedure', label: t('domainProcedure') },
    { id: 'offenses', label: t('domainOffenses') },
  ];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query, domain);
    }
  };

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-3xl space-y-8">
        <div className="text-center space-y-2">
          <h2 className="text-3xl font-bold text-primary font-serif">{t('askQuestion')}</h2>
          <p className="text-slate-500">{t('askQuestionEn')}</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="relative shadow-sm focus-within:shadow-md transition-shadow rounded-2xl bg-white border border-sandstone-border overflow-hidden">
            <textarea
              className={`w-full p-6 text-lg bg-transparent focus:outline-none resize-none min-h-[120px] ${isRTL ? 'text-right' : 'text-left'}`}
              placeholder={t('searchPlaceholder')}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e);
                }
              }}
            />
            <div className={`absolute bottom-4 ${isRTL ? 'left-4' : 'right-4'}`}>
              <button 
                type="submit"
                disabled={!query.trim()}
                className="p-3 bg-primary text-white rounded-full hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
              >
                <Search className="h-6 w-6" />
              </button>
            </div>
          </div>

          <div className="space-y-3">
            <p className="text-sm font-medium text-slate-600">{t('domains')}</p>
            <div className="flex flex-wrap gap-2">
              {domains.map((d) => (
                <button
                  key={d.id}
                  type="button"
                  onClick={() => setDomain(d.id)}
                  className={`px-4 py-2 rounded-full text-sm font-medium transition-colors border ${
                    domain === d.id 
                      ? 'bg-primary text-white border-primary' 
                      : 'bg-white text-slate-700 border-sandstone-border hover:border-primary/50'
                  }`}
                >
                  {d.label}
                </button>
              ))}
            </div>
          </div>
        </form>

        <div className="mt-12">
          <button className="w-full flex items-center justify-center gap-3 p-6 border-2 border-dashed border-sandstone-border rounded-2xl bg-white/50 text-slate-600 hover:bg-white hover:border-primary/50 hover:text-primary transition-all group">
            <UploadCloud className="h-6 w-6 text-slate-400 group-hover:text-primary" />
            <span className="font-medium text-lg">{t('uploadDoc')}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
