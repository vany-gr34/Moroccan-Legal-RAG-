import React from 'react';
import { Menu } from 'lucide-react';
import { Language, ViewState } from '../types';
import { getTranslation } from '../i18n';

interface NavbarProps {
  language: Language;
  setLanguage: (lang: Language) => void;
  currentView: ViewState;
  setView: (view: ViewState) => void;
}

export default function Navbar({ language, setLanguage, currentView, setView }: NavbarProps) {
  const t = (key: Parameters<typeof getTranslation>[1]) => getTranslation(language, key);
  const isRTL = language === 'ar';

  return (
    <nav className="h-16 bg-primary text-sandstone px-4 sm:px-8 flex items-center justify-between shadow-md">
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-3 cursor-pointer" onClick={() => setView('home')}>
          <div className="w-10 h-10 bg-sandstone rounded-full flex items-center justify-center shrink-0">
            <div className="w-6 h-6 border-2 border-primary rounded-sm transform rotate-45 flex items-center justify-center">
              <div className="w-2 h-2 bg-primary rounded-full"></div>
            </div>
          </div>
          <span className="text-xl font-bold tracking-tight">
            {t('appTitle')} <span className={`font-light opacity-80 uppercase text-xs ${isRTL ? 'mr-2' : 'ml-2'}`}>{t('appSubtitle')}</span>
          </span>
        </div>
        
        <div className="hidden md:block h-6 w-px bg-white/20"></div>
        
        <div className="hidden md:flex gap-4 text-sm font-medium">
          <button 
            onClick={() => setView('home')}
            className={`${currentView === 'home' || currentView === 'results' ? 'opacity-100 border-b-2 border-sandstone' : 'opacity-60 hover:opacity-100 transition-opacity'}`}
          >
            {t('askQuestion')}
          </button>
          <button 
            onClick={() => setView('knowledge_base')}
            className={`${currentView === 'knowledge_base' ? 'opacity-100 border-b-2 border-sandstone' : 'opacity-60 hover:opacity-100 transition-opacity'}`}
          >
            {t('manageKB')}
          </button>
          <button 
            onClick={() => setView('history')}
            className={`${currentView === 'history' ? 'opacity-100 border-b-2 border-sandstone' : 'opacity-60 hover:opacity-100 transition-opacity'}`}
          >
            {t('history')}
          </button>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex gap-2">
          <button
            onClick={() => setLanguage('ar')}
            className={`px-3 py-1 text-sm font-bold rounded transition-colors ${language === 'ar' ? 'bg-sandstone text-primary' : 'border border-sandstone text-sandstone opacity-60'}`}
          >
            AR
          </button>
          <button
            onClick={() => setLanguage('fr')}
            className={`px-3 py-1 text-sm font-bold rounded transition-colors ${language === 'fr' ? 'bg-sandstone text-primary' : 'border border-sandstone text-sandstone opacity-60'}`}
          >
            FR
          </button>
        </div>
        <div className="hidden md:flex w-8 h-8 rounded-full bg-blue-900 border border-white/20 items-center justify-center text-xs shrink-0 font-bold">
          JD
        </div>
        <button className="md:hidden p-2 rounded-md hover:bg-white/10 focus:outline-none">
          <Menu className="h-6 w-6" />
        </button>
      </div>
    </nav>
  );
}
