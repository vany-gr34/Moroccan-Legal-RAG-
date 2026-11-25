import React from 'react';
import { Search, Clock, Trash2, ChevronRight, ChevronLeft } from 'lucide-react';
import { Language, HistoryItem } from '../types';
import { getTranslation } from '../i18n';

interface HistoryViewProps {
  language: Language;
}

export default function HistoryView({ language }: HistoryViewProps) {
  const t = (key: Parameters<typeof getTranslation>[1]) => getTranslation(language, key);
  const isRTL = language === 'ar';
  const ChevronIcon = isRTL ? ChevronLeft : ChevronRight;

  const mockHistoryData = [
    {
      group: t('today'),
      items: [
        { id: '1', timestamp: '10:30', query: 'ما عقوبة تجاوز السرعة في المدار الحضري؟', domain: 'السير', sourcesCount: 3 },
        { id: '2', timestamp: '09:15', query: 'كيف يتم الطلاق الاتفاقي؟', domain: 'الأسرة', sourcesCount: 4 },
      ]
    },
    {
      group: t('yesterday'),
      items: [
        { id: '3', timestamp: '16:45', query: 'شروط صحة العقد في القانون المدني', domain: 'المدني', sourcesCount: 2 },
      ]
    }
  ];

  return (
    <div className="flex-1 w-full max-w-4xl mx-auto px-4 py-8 space-y-6">
      <div className="flex items-center justify-between border-b border-sandstone-border pb-4">
        <h2 className="text-2xl font-bold text-slate-900 font-serif">{t('history')}</h2>
        <button className="flex items-center px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50 rounded-md transition-colors">
          <Trash2 className={`h-4 w-4 ${isRTL ? 'ml-2' : 'mr-2'}`} />
          {t('clearHistory')}
        </button>
      </div>

      <div className="relative mb-6">
        <div className={`absolute inset-y-0 ${isRTL ? 'right-0 pr-3' : 'left-0 pl-3'} flex items-center pointer-events-none`}>
          <Search className="h-5 w-5 text-slate-400" />
        </div>
        <input
          type="text"
          className={`block w-full rounded-lg border border-sandstone-border py-3 ${isRTL ? 'pr-10 pl-3' : 'pl-10 pr-3'} text-sm placeholder-slate-400 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary bg-white`}
          placeholder={t('searchHistory')}
        />
      </div>

      <div className="space-y-8">
        {mockHistoryData.map((group, idx) => (
          <div key={idx} className="space-y-4">
            <h3 className="text-sm font-bold text-slate-500 uppercase tracking-wider">{group.group}</h3>
            <div className="bg-white rounded-xl shadow-sm border border-sandstone-border overflow-hidden divide-y divide-sandstone-border">
              {group.items.map((item) => (
                <div key={item.id} className="p-4 flex items-center justify-between hover:bg-slate-50 transition-colors cursor-pointer group/item">
                  <div className="flex items-start space-x-4 space-x-reverse={isRTL}">
                    <div className="text-xs font-mono text-slate-400 mt-1">{item.timestamp}</div>
                    <div>
                      <h4 className="text-slate-800 font-medium group-hover/item:text-primary transition-colors">{item.query}</h4>
                      <div className="flex items-center text-xs text-slate-500 mt-1 space-x-2 space-x-reverse={isRTL}">
                        <span className="bg-slate-100 px-2 py-0.5 rounded text-slate-600">{item.domain}</span>
                        <span>·</span>
                        <span>{item.sourcesCount} {t('sourcesCount')}</span>
                      </div>
                    </div>
                  </div>
                  <button className="flex items-center text-sm font-medium text-primary opacity-0 group-hover/item:opacity-100 transition-opacity">
                    {t('view')} <ChevronIcon className="h-4 w-4 mx-1" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
