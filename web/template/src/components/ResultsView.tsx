import React, { useState } from 'react';
import { ThumbsUp, ThumbsDown, Copy } from 'lucide-react';
import { Language, QueryResult, SourceArticle } from '../types';
import { getTranslation } from '../i18n';

interface ResultsViewProps {
  language: Language;
  result: QueryResult;
  onSourceClick: (source: SourceArticle) => void;
  onBack: () => void;
}

export default function ResultsView({ language, result, onSourceClick, onBack }: ResultsViewProps) {
  const isRTL = language === 'ar';
  
  const [activeTab, setActiveTab] = useState<'legal' | 'simple'>('legal');

  // Hardcode translated labels for simplicity during the layout matching
  const tLegalAns = isRTL ? 'الإجابة القانونية المقترحة' : 'Suggested Legal Answer';
  const tLegalTab = isRTL ? 'لغة قانونية' : 'Legal language';
  const tSimpleTab = isRTL ? 'تفسير مبسط' : 'Simplified explanation';
  const tHelpful = isRTL ? 'هل كانت هذه المعلومة دقيقة ومفيدة؟' : 'Was this information accurate and helpful?';
  const tYes = isRTL ? 'نعم' : 'Yes';
  const tNo = isRTL ? 'لا' : 'No';
  const tCopy = isRTL ? 'نسخ مع المصادر' : 'Copy with sources';
  const tSources = isRTL ? 'المصادر القانونية' : 'Legal Sources';
  const tRelevance = isRTL ? 'صلة:' : 'Relevance:';
  const tViewFull = isRTL ? 'عرض النص الكامل ←' : 'View full text →';
  const tViewMore = isRTL ? 'عرض مصادر إضافية' : 'View additional sources';

  return (
    <div className="flex-1 flex flex-col h-full bg-white overflow-hidden">
      {/* Query Context Header */}
      <div className="h-20 bg-white border-b border-sandstone-border flex items-center justify-between px-8 shrink-0">
        <div className="flex flex-col">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-widest">
            {isRTL ? 'سؤالك الحالي' : 'Current Query'}
          </span>
          <h1 className="text-xl font-medium text-slate-900">{result.query}</h1>
        </div>
        <div className="flex gap-3">
          <div className="px-4 py-2 bg-sandstone rounded-lg flex items-center gap-2 border border-sandstone-border">
            <span className="text-xs font-semibold text-gray-500">{isRTL ? 'المجال:' : 'Domain:'}</span>
            <span className="text-sm font-bold text-slate-800">{result.domain}</span>
          </div>
          <button onClick={onBack} className="px-6 py-2 bg-primary text-white rounded-lg text-sm font-bold shadow-sm hover:opacity-90 transition-opacity">
            {isRTL ? 'تعديل السؤال' : 'Edit Query'}
          </button>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar / Knowledge Base Status */}
        <aside className="w-64 bg-sandstone-alt border-r border-sandstone-border p-6 flex flex-col gap-6 shrink-0 rtl:border-r-0 rtl:border-l">
          <div>
            <h3 className="text-xs font-bold text-gray-500 mb-4 uppercase tracking-wider">
              {isRTL ? 'قاعدة البيانات النشطة' : 'Active Databases'}
            </h3>
            <ul className="space-y-3">
              <li className="flex items-center gap-3 p-2 bg-white rounded border border-sandstone-border shadow-sm">
                <div className="w-2 h-2 rounded-full bg-green-500"></div>
                <span className="text-sm font-medium text-slate-800">{isRTL ? 'مدونة السير 2024' : 'Traffic Code 2024'}</span>
              </li>
              <li className="flex items-center gap-3 p-2 bg-white/50 rounded border border-sandstone-border opacity-70">
                <div className="w-2 h-2 rounded-full bg-green-500"></div>
                <span className="text-sm font-medium text-slate-800">{isRTL ? 'القانون الجنائي' : 'Criminal Code'}</span>
              </li>
              <li className="flex items-center gap-3 p-2 bg-white/50 rounded border border-sandstone-border opacity-70">
                <div className="w-2 h-2 rounded-full bg-green-500"></div>
                <span className="text-sm font-medium text-slate-800">{isRTL ? 'مدونة الأسرة' : 'Family Code'}</span>
              </li>
            </ul>
          </div>
          <div className="mt-auto p-4 bg-primary/5 border border-primary/10 rounded-xl">
            <p className="text-xs leading-relaxed text-gray-600">
              {isRTL 
                ? 'يتم تحديث النصوص القانونية بشكل آلي من الجريدة الرسمية للمملكة المغربية.'
                : 'Legal texts are automatically updated from the Official Gazette.'}
            </p>
            <button className="mt-3 text-xs font-bold underline text-slate-700">
              {isRTL ? 'عرض آخر التحديثات' : 'View latest updates'}
            </button>
          </div>
        </aside>

        {/* Split Result Panels */}
        <main className="flex-1 flex overflow-hidden bg-white/30 hidden md:flex">
          {/* Left Panel: AI Answer */}
          <div className="w-3/5 p-8 overflow-y-auto bg-white rtl:border-l ltr:border-r border-sandstone-border">
            <div className="flex flex-col xl:flex-row xl:items-center justify-between mb-6 gap-4">
              <h2 className="text-lg text-slate-900 font-bold flex items-center gap-2">
                <span className="w-2 h-6 bg-success rounded-full"></span>
                {tLegalAns}
              </h2>
              <div className="bg-sandstone p-1 rounded-lg flex shrink-0">
                <button 
                  onClick={() => setActiveTab('legal')}
                  className={`px-4 py-1 text-xs font-bold rounded shadow-sm ${activeTab === 'legal' ? 'bg-white text-slate-800' : 'text-gray-500 transparent'}`}
                >
                  {tLegalTab}
                </button>
                <button 
                  onClick={() => setActiveTab('simple')}
                  className={`px-4 py-1 text-xs font-bold rounded shadow-sm ${activeTab === 'simple' ? 'bg-white text-slate-800' : 'text-gray-500 transparent'}`}
                >
                  {tSimpleTab}
                </button>
              </div>
            </div>
            
            <div className="prose prose-blue text-primary leading-loose font-serif">
              <div className="mb-4 text-lg whitespace-pre-wrap">
                {activeTab === 'legal' ? result.answerLegal : result.answerSimple}
              </div>
              <div className="p-4 bg-blue-50 border-blue-600 italic text-sm rtl:border-r-4 ltr:border-l-4 rounded-sm">
                تنبيه: هذا الجواب للاسترشاد، ويفضل دائما العودة للجهات المختصة.
              </div>
            </div>

            {/* Feedback Section */}
            <div className="mt-12 pt-6 border-t border-sandstone-border flex items-center justify-between">
              <span className="text-sm text-gray-500">{tHelpful}</span>
              <div className="flex gap-4 items-center">
                <button className="flex items-center gap-2 px-4 py-2 hover:bg-gray-100 rounded-lg transition-colors text-slate-700">
                  <span>👍</span> <span className="text-sm">{tYes}</span>
                </button>
                <button className="flex items-center gap-2 px-4 py-2 hover:bg-gray-100 rounded-lg transition-colors text-slate-700">
                  <span>👎</span> <span className="text-sm">{tNo}</span>
                </button>
                <button className={`px-4 py-2 border border-sandstone-border rounded-lg text-sm font-bold text-slate-700 hover:bg-slate-50 ${isRTL ? 'mr-4' : 'ml-4'}`}>
                  {tCopy}
                </button>
              </div>
            </div>
          </div>

          {/* Right Panel: Source Articles */}
          <div className="w-2/5 p-6 overflow-y-auto bg-sandstone/40">
            <h3 className="text-sm font-bold text-gray-500 mb-4 uppercase tracking-widest">
              {tSources} ({result.sources.length})
            </h3>
            
            <div className="space-y-4">
              {result.sources.map((source) => (
                <div 
                  key={source.id}
                  onClick={() => onSourceClick(source)}
                  className="bg-white rounded-xl border border-sandstone-border overflow-hidden shadow-sm hover:border-primary transition-colors cursor-pointer group"
                >
                  <div className="bg-sandstone p-3 flex justify-between items-center border-b border-sandstone-border">
                    <span className="text-xs font-bold text-slate-900 line-clamp-1">{source.title}</span>
                    <span className="px-2 py-0.5 bg-success/10 text-success rounded text-[10px] font-bold whitespace-nowrap shrink-0">
                      {tRelevance} {source.relevance}%
                    </span>
                  </div>
                  <div className="p-4">
                    <p className="text-sm line-clamp-3 leading-relaxed opacity-80 text-slate-800">
                      "{source.snippet}"
                    </p>
                    <div className="mt-3 flex justify-end">
                      <span className="text-[10px] font-bold text-primary group-hover:underline">
                        {tViewFull}
                      </span>
                    </div>
                  </div>
                </div>
              ))}

              <div className="bg-white rounded-xl border border-dashed border-sandstone-border p-4 text-center">
                <button className="text-xs font-bold opacity-60 hover:opacity-100 text-slate-700">
                  {tViewMore}
                </button>
              </div>
            </div>
          </div>
        </main>
      </div>

      {/* Bottom Status Bar */}
      <footer className="h-8 bg-primary text-[10px] text-white/60 flex items-center justify-between px-6 shrink-0">
        <div className="flex gap-4">
          <span>{isRTL ? 'رقم الجلسة: #99283-A' : 'Session: #99283-A'}</span>
          <span>{isRTL ? 'وقت المعالجة: 1.2 ثانية' : 'Processing time: 1.2s'}</span>
        </div>
        <div className="flex gap-4">
          <span>{isRTL ? 'المملكة المغربية - وزارة العدل (بيانات عامة)' : 'Kingdom of Morocco - MoJ (Public Data)'}</span>
          <span className="text-white font-bold">{isRTL ? 'حالة النظام: متصل' : 'System Status: Online'}</span>
        </div>
      </footer>
    </div>
  );
}
