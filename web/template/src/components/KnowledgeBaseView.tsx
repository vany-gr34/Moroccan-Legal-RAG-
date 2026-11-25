import React from 'react';
import { UploadCloud, FileText, Activity, Clock, CheckCircle2, AlertCircle } from 'lucide-react';
import { Language, KBItem } from '../types';
import { getTranslation } from '../i18n';

interface KnowledgeBaseViewProps {
  language: Language;
}

export default function KnowledgeBaseView({ language }: KnowledgeBaseViewProps) {
  const t = (key: Parameters<typeof getTranslation>[1]) => getTranslation(language, key);
  const isRTL = language === 'ar';

  const mockDocs: KBItem[] = [
    { id: '1', title: 'مدونة السير (Code de la route)', status: 'active', lastUpdated: '2024-01-15', articleCount: 180 },
    { id: '2', title: 'القانون الجنائي (Code pénal)', status: 'active', lastUpdated: '2024-03-20', articleCount: 450 },
    { id: '3', title: 'مدونة الأسرة (Code de la famille)', status: 'active', lastUpdated: '2023-11-05', articleCount: 200 },
    { id: '4', title: 'مرسوم جديد (Nouveau décret)', status: 'processing', lastUpdated: '2024-06-10', articleCount: 0 },
  ];

  return (
    <div className="flex-1 w-full max-w-4xl mx-auto px-4 py-8 space-y-8">
      <div className="flex items-center space-x-3 space-x-reverse={isRTL} border-b border-sandstone-border pb-4">
        <h2 className="text-2xl font-bold text-slate-900 font-serif">{t('manageKB')}</h2>
      </div>

      {/* Upload Zone */}
      <div className="bg-white p-8 rounded-xl border-2 border-dashed border-sandstone-border flex flex-col items-center justify-center text-center cursor-pointer hover:bg-slate-50 transition-colors group">
        <div className="p-4 bg-primary/10 rounded-full mb-4 group-hover:scale-110 transition-transform">
          <UploadCloud className="h-8 w-8 text-primary" />
        </div>
        <h3 className="text-lg font-semibold text-slate-900 mb-2">{t('uploadNewDoc')}</h3>
        <p className="text-slate-500 text-sm max-w-sm">{t('dragDropDoc')}</p>
      </div>

      {/* Documents List */}
      <div className="bg-white rounded-xl shadow-sm border border-sandstone-border overflow-hidden">
        <div className="p-5 border-b border-sandstone-border bg-sandstone">
          <h3 className="font-semibold text-slate-900">{t('documentsList')}</h3>
        </div>
        <div className="divide-y divide-sandstone-border">
          {mockDocs.map((doc) => (
            <div key={doc.id} className="p-5 flex items-center justify-between hover:bg-slate-50 transition-colors">
              <div className="flex items-start space-x-4 space-x-reverse={isRTL}">
                <div className={`p-2 rounded-lg ${doc.status === 'active' ? 'bg-success/10 text-success' : 'bg-amber-100 text-amber-600'}`}>
                  <FileText className="h-6 w-6" />
                </div>
                <div>
                  <h4 className="font-semibold text-slate-800">{doc.title}</h4>
                  <div className="flex items-center space-x-4 space-x-reverse={isRTL} mt-1 text-xs text-slate-500">
                    <span className="flex items-center">
                      <Clock className={`h-3 w-3 ${isRTL ? 'ml-1' : 'mr-1'}`} />
                      {t('lastUpdate')} {doc.lastUpdated}
                    </span>
                    {doc.articleCount > 0 && (
                      <span className="flex items-center">
                        <Activity className={`h-3 w-3 ${isRTL ? 'ml-1' : 'mr-1'}`} />
                        {doc.articleCount} {t('articlesCount')}
                      </span>
                    )}
                  </div>
                </div>
              </div>
              
              <div className="flex items-center space-x-4 space-x-reverse={isRTL}">
                {doc.status === 'active' ? (
                   <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-success/10 text-success border border-success/20">
                     <CheckCircle2 className={`h-3 w-3 ${isRTL ? 'ml-1' : 'mr-1'}`} />
                     {t('statusActive')}
                   </span>
                ) : (
                  <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-700 border border-amber-200">
                     <AlertCircle className={`h-3 w-3 ${isRTL ? 'ml-1' : 'mr-1'} animate-pulse`} />
                     {t('statusProcessing')}
                   </span>
                )}
                
                {/* Toggle switch placeholder */}
                <div className={`w-11 h-6 rounded-full flex items-center p-1 cursor-pointer transition-colors ${doc.status === 'active' ? 'bg-primary' : 'bg-slate-300 pointer-events-none opacity-50'}`}>
                  <div className={`w-4 h-4 rounded-full bg-white shadow-sm transform transition-transform ${isRTL ? (doc.status === 'active' ? '-translate-x-5' : 'translate-x-0') : (doc.status === 'active' ? 'translate-x-5' : 'translate-x-0')}`} />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
