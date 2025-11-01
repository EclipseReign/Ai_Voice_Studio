import React, { useState, useEffect } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../contexts/AuthContext";
import { API } from "../App";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { toast } from "sonner";
import { Loader2, Sparkles, Mic, Download, Clock, Volume2, User, LogOut } from "lucide-react";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { ThemeSwitcher } from "@/components/ThemeSwitcher";

const HomePage = () => {
  const { t } = useTranslation();
  const { user, subscription, logout, isAdmin, refreshSubscription } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("ai-generate");
  
  // AI Generation state
  const [prompt, setPrompt] = useState("");
  const [duration, setDuration] = useState(1);
  const [generatedText, setGeneratedText] = useState("");
  const [isGeneratingText, setIsGeneratingText] = useState(false);
  
  // Progress tracking (enhanced with ETA and speed)
  const [textProgress, setTextProgress] = useState(0);
  const [textProgressMessage, setTextProgressMessage] = useState("");
  const [audioProgress, setAudioProgress] = useState(0);
  const [audioProgressMessage, setAudioProgressMessage] = useState("");
  const [audioEta, setAudioEta] = useState("");
  const [audioSpeed, setAudioSpeed] = useState(0);
  const [audioStage, setAudioStage] = useState("");
  const [completedSegments, setCompletedSegments] = useState(0);
  const [totalSegments, setTotalSegments] = useState(0);
  const [queuePosition, setQueuePosition] = useState(0);
  const [generationTime, setGenerationTime] = useState(0);
  
  // Manual input state
  const [manualText, setManualText] = useState("");
  
  // Common state
  const [voices, setVoices] = useState([]);
  const [selectedVoice, setSelectedVoice] = useState("");
  const [language, setLanguage] = useState("en-US");
  const [speed, setSpeed] = useState([0]);
  const [isSynthesizing, setIsSynthesizing] = useState(false);
  const [audioUrl, setAudioUrl] = useState(null);
  const [audioDuration, setAudioDuration] = useState(0);
  const [currentAudioId, setCurrentAudioId] = useState(null); // Track current audio ID for cleanup
  const [history, setHistory] = useState([]);
  
  // Video generation state
  const [isGeneratingVideo, setIsGeneratingVideo] = useState(false);
  const [videoType, setVideoType] = useState("youtube_images");
  const [videoProgress, setVideoProgress] = useState(0);
  const [videoProgressMessage, setVideoProgressMessage] = useState("");
  const [videoStage, setVideoStage] = useState("");
  const [currentVideoId, setCurrentVideoId] = useState(null);
  const [videoUrl, setVideoUrl] = useState(null);
  const [videoDuration, setVideoDuration] = useState(0);
  const [currentTextId, setCurrentTextId] = useState(null); // Track text ID for video generation
  const [videoHistory, setVideoHistory] = useState([]);
  
  // Fetch voices on mount
  useEffect(() => {
    fetchVoices();
    fetchHistory();
    fetchVideoHistory(); // Fetch video history on mount
    checkPendingJobs(); // NEW: Check for pending jobs on mount (recovery)
  }, []);
  
  // Update selected voice when language changes
  useEffect(() => {
    if (voices.length > 0) {
      const voicesForLang = getVoicesByLanguage();
      if (voicesForLang.length > 0) {
        // Only update if current voice is not in the new language
        const currentVoiceInList = voicesForLang.find(v => v.short_name === selectedVoice);
        if (!currentVoiceInList) {
          setSelectedVoice(voicesForLang[0].short_name);
        }
      }
    }
  }, [language, voices]);
  
  const fetchVoices = async () => {
    try {
      const response = await axios.get(API + '/voices', {
        withCredentials: true
      });
      setVoices(response.data);
      if (response.data.length > 0) {
        // Set first voice for current language
        const langCode = language.split('-')[0].toLowerCase();
        const voicesForLang = response.data.filter(v => v.locale.toLowerCase().startsWith(langCode));
        if (voicesForLang.length > 0) {
          setSelectedVoice(voicesForLang[0].short_name);
        } else {
          setSelectedVoice(response.data[0].short_name);
        }
      }
    } catch (error) {
      console.error("Error fetching voices:", error);
      toast.error(t('notifications.failedToLoadVoices'));
    }
  };
  
  const fetchHistory = async () => {
    try {
      const response = await axios.get(API + '/history', {
        withCredentials: true
      });
      setHistory(response.data);
    } catch (error) {
      console.error("Error fetching history:", error);
    }
  };
  
  // NEW: Reset generation state after completion (to free memory)
  const resetGenerationState = () => {
    setAudioProgress(0);
    setAudioProgressMessage("");
    setTextProgress(0);
    setTextProgressMessage("");
    setAudioEta("");
    setAudioSpeed(0);
    setAudioStage("");
    setCompletedSegments(0);
    setTotalSegments(0);
    setQueuePosition(0);
    setGenerationTime(0);
  };
  
  // NEW: Check for pending jobs on mount (recovery after page refresh/crash)
  const checkPendingJobs = async () => {
    try {
      const response = await axios.get(API + '/jobs/pending', {
        withCredentials: true
      });
      
      if (response.data && response.data.length > 0) {
        const pendingJob = response.data[0]; // Get most recent pending job
        
        // Show toast notification about recovery option
        toast.info(
          t('notifications.pendingJobFound', { percent: pendingJob.progress_percent }),
          {
            duration: 10000,
            action: {
              label: t('notifications.continue'),
              onClick: () => resumeJob(pendingJob.job_id)
            }
          }
        );
      }
    } catch (error) {
      console.error("Error checking pending jobs:", error);
    }
  };
  
  // NEW: Resume a pending job
  const resumeJob = async (jobId) => {
    try {
      // Call backend to resume job
      const response = await axios.post(
        API + `/jobs/resume/${jobId}`,
        {},
        { withCredentials: true }
      );
      
      toast.success(t('notifications.continueGeneration'));
      // The backend will continue generating and send SSE updates
    } catch (error) {
      console.error("Error resuming job:", error);
      toast.error(t('notifications.failedToContinue'));
    }
  };
  
  // Delete audio file (user-initiated only)
  const deleteAudioFile = async (audioId) => {
    try {
      const response = await axios.post(
        API + `/audio/cleanup/${audioId}`,
        {},
        { withCredentials: true }
      );
      
      toast.success(t('notifications.fileDeleted', { mb: response.data.freed_mb }));
      fetchHistory(); // Refresh history
    } catch (error) {
      console.error("Error deleting audio:", error);
      toast.error(t('notifications.failedToDelete'));
    }
  };
  
  // NEW: Download text as .txt file
  const downloadText = async (audioId) => {
    try {
      const response = await fetch(API + `/text/download/${audioId}`, {
        method: 'GET',
        credentials: 'include'
      });
      
      if (!response.ok) {
        throw new Error('Download failed');
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `text_${audioId}.txt`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      toast.success(t('notifications.textDownloaded'));
    } catch (error) {
      console.error("Error downloading text:", error);
      toast.error(t('notifications.failedToDownloadText'));
    }
  };

// NEW: Download video as .mp4 file
  const downloadVideo = async (videoId) => {
    try {
      const response = await fetch(API + `/video/download/${videoId}`, {
        method: 'GET',
        credentials: 'include'
      });
      
      if (!response.ok) {
        throw new Error('Download failed');
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `video_${videoId}.mp4`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      toast.success(t('notifications.videoDownloaded'));
    } catch (error) {
      console.error("Error downloading video:", error);
      toast.error(t('notifications.failedToDownloadVideo'));
    }
  };
  
  const handleGenerateText = async () => {
    if (!prompt.trim()) {
      toast.error(t('notifications.enterPrompt'));
      return;
    }
    
    setIsGeneratingText(true);
    setTextProgress(0);
    setTextProgressMessage(t('progress.startingGeneration'));
    setGeneratedText("");
    
    try {
      // Use fetch with streaming for SSE (supports credentials)
      const response = await fetch(
        `${API}/text/generate-with-progress?` + new URLSearchParams({
          prompt: prompt,
          duration_minutes: duration,
          language: language
        }),
        {
          credentials: 'include', // Send cookies
          headers: {
            'Accept': 'text/event-stream'
          }
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              if (data.type === 'info') {
                setTextProgressMessage(data.message);
                if (data.progress !== undefined) {
                  setTextProgress(data.progress);
                }
              } else if (data.type === 'progress') {
                setTextProgress(data.progress);
                if (data.message) {
                  setTextProgressMessage(data.message);
                }
              } else if (data.type === 'complete') {
                setTextProgress(100);
                setTextProgressMessage(t('progress.done'));
                setGeneratedText(data.text);
                setCurrentTextId(data.text_id); // Save text ID for video generation
                toast.success(t('notifications.textGenerated', { count: data.word_count }));
                setIsGeneratingText(false);
                // Refresh subscription to update usage count
                await refreshSubscription();
              } else if (data.type === 'error') {
                toast.error(data.message || t('notifications.textGenerationError'))
                setIsGeneratingText(false);
                await refreshSubscription();
              }
            } catch (error) {
              console.error("Error parsing SSE data:", error);
            }
          }
        }
      }
      
    } catch (error) {
      console.error("Error generating text:", error);
      toast.error(t('notifications.failedToGenerateText'));
      setIsGeneratingText(false);
    }
  };
  
  const handleSynthesize = async (textOverride = null, jobId = null) => {
    // Use provided text or fall back to current text based on active tab
    const text = textOverride || (activeTab === "ai-generate" ? generatedText : manualText);
    
    if (!text.trim()) {
      toast.error(t('notifications.enterText'));
      return;
    }
    
    if (!selectedVoice) {
      toast.error(t('notifications.selectVoice'));
      return;
    }
    
    setIsSynthesizing(true);
    setAudioProgress(0);
    setAudioProgressMessage(jobId ? t('progress.preparingContinuation') : t('progress.preparing'));
    setAudioUrl(null);
    setAudioEta("");
    setAudioSpeed(0);
    setAudioStage("");
    setCompletedSegments(0);
    setTotalSegments(0);
    setQueuePosition(0);
    setGenerationTime(0);
    
    try {
      const speedValue = speed[0];
      const rate = 1.0 + (speedValue / 100);
      
      console.log("Synthesizing with voice:", selectedVoice, "rate:", rate);
      
      // Use fetch with streaming for SSE (supports credentials)
      // Using POST method to support large texts (up to 1 hour audio)
      // GET method has URL length limits (~8000 chars) which is insufficient for long texts
      const response = await fetch(
        `${API}/audio/synthesize-with-progress`,
        {
          method: 'POST',
          credentials: 'include', // Send cookies
          headers: {
            'Accept': 'text/event-stream',
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            text: text,
            voice: selectedVoice,
            rate: rate,
            language: language
          })
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              if (data.type === 'queue') {
                // In queue
                setAudioProgress(0);
                setAudioProgressMessage(data.message);
                setQueuePosition(data.queue_position || 0);
              } else if (data.type === 'high_load') {
                // NEW: High load notification
                toast.warning(data.message, { duration: 5000 });
              } else if (data.type === 'stage') {
                // New stage started
                setAudioStage(data.stage);
                setAudioProgressMessage(data.message);
                setAudioProgress(data.progress);
                if (data.total_segments) {
                  setTotalSegments(data.total_segments);
                }
              } else if (data.type === 'progress') {
                // Progress update
                setAudioProgress(data.progress);
                setAudioProgressMessage(data.message);
                if (data.stage) {
                  setAudioStage(data.stage);
                }
                if (data.completed_segments !== undefined) {
                  setCompletedSegments(data.completed_segments);
                }
                if (data.total_segments !== undefined) {
                  setTotalSegments(data.total_segments);
                }
                if (data.eta) {
                  setAudioEta(data.eta);
                }
                if (data.speed !== undefined) {
                  setAudioSpeed(data.speed);
                }
              } else if (data.type === 'info') {
                setAudioProgressMessage(data.message);
                if (data.progress !== undefined) {
                  setAudioProgress(data.progress);
                }
              } else if (data.type === 'complete') {
                setAudioProgress(100);
                setAudioProgressMessage(data.message || t('progress.done'));
                setAudioUrl(API + data.audio_url);
                setAudioDuration(data.duration || 0);
                setCurrentAudioId(data.audio_id);
                if (data.text_id) {
                  setCurrentTextId(data.text_id);
                }
                setGenerationTime(data.generation_time || 0);
                if (data.speed) {
                  setAudioSpeed(data.speed);
                }
                toast.success(data.message || t('notifications.audioGenerated'));
                fetchHistory();
                setIsSynthesizing(false);
                
                // Files are now stored permanently - no auto-cleanup
                // User can manually delete from history if needed
                
                // Refresh subscription to update usage count
                await refreshSubscription();
              } else if (data.type === 'error') {
                toast.error(data.message);
                setIsSynthesizing(false);
              }
            } catch (e) {
              console.error("Error parsing SSE data:", e);
            }
          }
        }
      }
      
    } catch (error) {
      console.error("Error synthesizing audio:", error);
      toast.error(t('notifications.failedToGenerateAudio'));
      setIsSynthesizing(false);
    }
  };
  
  const handleGenerateVideo = async () => {
    if (!currentTextId || !currentAudioId) {
      toast.error(t('notifications.createTextAndAudioFirst'));
      return;
    }
    
    setIsGeneratingVideo(true);
    setVideoProgress(0);
    setVideoProgressMessage(t('progress.startingVideoGeneration'));
    setVideoUrl(null);
    setVideoStage("");
    
    try {
      const response = await fetch(
        `${API}/video/generate-with-progress`,
        {
          method: 'POST',
          credentials: 'include',
          headers: {
            'Accept': 'text/event-stream',
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            text_id: currentTextId,
            audio_id: currentAudioId,
            video_type: videoType
          })
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              if (data.type === 'started') {
                setVideoProgressMessage(data.message);
                setCurrentVideoId(data.job_id);
              } else if (data.type === 'stage') {
                setVideoStage(data.stage);
                setVideoProgressMessage(data.message);
                if (data.progress !== undefined) {
                  setVideoProgress(data.progress);
                }
              } else if (data.type === 'progress') {
                setVideoProgress(data.progress);
                setVideoProgressMessage(data.message);
                setVideoStage(data.stage);
              } else if (data.type === 'complete') {
                setVideoProgress(100);
                setVideoProgressMessage(t('progress.videoReady'));
                setVideoUrl(API + data.video_url);
                setVideoDuration(data.duration || 0);
                toast.success(t('notifications.videoCreated'));
                fetchVideoHistory();
                setIsGeneratingVideo(false);
              } else if (data.type === 'error') {
                toast.error(data.message);
                setIsGeneratingVideo(false);
              }
            } catch (e) {
              console.error("Error parsing SSE data:", e);
            }
          }
        }
      }
      
    } catch (error) {
      console.error("Error generating video:", error);
      toast.error(t('notifications.failedToGenerateVideo'));
      setIsGeneratingVideo(false);
    }
  };
  
  const fetchVideoHistory = async () => {
    try {
      const response = await axios.get(`${API}/video/history`, {
        withCredentials: true
      });
      setVideoHistory(response.data.videos || []);
    } catch (error) {
      console.error("Error fetching video history:", error);
    }
  };
  
  const getVoicesByLanguage = () => {
    const langCode = language.split('-')[0].toLowerCase();
    return voices.filter(v => v.locale.toLowerCase().startsWith(langCode));
  };
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-slate-900 dark:to-slate-800 transition-colors duration-300">
      {/* Top Navigation Bar */}
      <div className="bg-white dark:bg-slate-900 shadow-sm border-b border-gray-200 dark:border-slate-700 transition-colors duration-300">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-4">
              <h1 className="text-xl font-bold text-gray-900 dark:text-white">🎙️ AI Voice Studio</h1>
              {subscription && (
                <div className="flex items-center gap-3">
                  <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                    subscription.tier === 'pro'
                      ? 'bg-gradient-to-r from-purple-100 to-pink-100 dark:from-purple-900 dark:to-pink-900 text-purple-800 dark:text-purple-200 border border-purple-200 dark:border-purple-700'
                      : 'bg-gray-100 dark:bg-slate-800 text-gray-700 dark:text-gray-300'
                  }`}>
                    {subscription.tier === 'pro' ? '✨ Pro' : 'Free'}
                  </span>
                  {subscription.tier === 'free' && (
                    <div className="flex items-center gap-2 text-xs">
                      <span className="text-gray-600 dark:text-gray-400">
                        📝 {subscription.text_usage_today}/{subscription.text_limit}
                      </span>
                      <span className="text-gray-400 dark:text-gray-600">•</span>
                      <span className="text-gray-600 dark:text-gray-400">
                        🎵 {subscription.audio_usage_today}/{subscription.audio_limit}
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>
            <div className="flex items-center space-x-3">
              {/* Language Switcher */}
              <LanguageSwitcher />
              
              {/* Theme Switcher */}
              <ThemeSwitcher variant="icon-only" showLabel={false} />
              {subscription && subscription.tier === 'free' && (
                <button
                  onClick={() => navigate('/pricing')}
                  className="px-4 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-lg hover:from-purple-700 hover:to-indigo-700 transition-all text-sm font-semibold shadow-md"
                >
                  ⚡ Upgrade to Pro
                </button>
              )}
              <button
                onClick={() => navigate('/dashboard')}
                className="flex items-center space-x-2 px-4 py-2 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
              >
                <User className="w-4 h-4" />
                <span>{user?.name?.split(' ')[0] || 'Profile'}</span>
              </button>
              {isAdmin && (
                <button
                  onClick={() => navigate('/admin')}
                  className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors text-sm font-semibold"
                >
                  ⚙️ Admin
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-6">
        {/* Header */}
        <div className="text-center mb-8 pt-4">
          <h2 className="text-4xl lg:text-5xl font-bold mb-3 bg-gradient-to-r from-blue-600 to-cyan-600 dark:from-blue-400 dark:to-cyan-400 bg-clip-text text-transparent" data-testid="main-heading">
          </h2>
          <p className="text-lg text-slate-600 dark:text-slate-300">{t('home.subtitle')}</p>
        </div>
        
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2">
            <Card className="backdrop-blur-sm bg-white/80 border-slate-200 shadow-xl" data-testid="main-card">
              <CardHeader>
                <CardTitle className="text-2xl">{t('home.createVoiceNarration')}</CardTitle>
                <CardDescription>{t('home.chooseGenerationMethod')}</CardDescription>
              </CardHeader>
              <CardContent>
                <Tabs value={activeTab} onValueChange={setActiveTab}>
                  <TabsList className="grid w-full grid-cols-2 mb-6" data-testid="mode-tabs">
                    <TabsTrigger value="ai-generate" data-testid="ai-generate-tab">
                      <Sparkles className="w-4 h-4 mr-2" />
                      {t('home.aiGeneration')}
                    </TabsTrigger>
                    <TabsTrigger value="manual-input" data-testid="manual-input-tab">
                      <Mic className="w-4 h-4 mr-2" />
                      {t('home.manualInput')}
                    </TabsTrigger>
                  </TabsList>
                  
                  {/* AI Generate Tab */}
                  <TabsContent value="ai-generate" className="space-y-6">
                    <div className="space-y-4">
                      <div>
                        <Label htmlFor="prompt">{t('home.topicPrompt')}</Label>
                        <Textarea
                          id="prompt"
                          data-testid="ai-prompt-input"
                          placeholder={t('home.promptPlaceholderLong')}
                          value={prompt}
                          onChange={(e) => setPrompt(e.target.value)}
                          rows={3}
                          className="mt-2"
                        />
                      </div>
                      
                      <div className="grid md:grid-cols-2 gap-4">
                        <div>
                          <Label htmlFor="duration">
                            <Clock className="w-4 h-4 inline mr-2" />
                            {t('home.targetDuration')}: {duration} {duration !== 1 ? t('home.minutes') : t('home.minute')}
                          </Label>
                          <Slider
                            id="duration"
                            data-testid="duration-slider"
                            value={[duration]}
                            onValueChange={(val) => setDuration(val[0])}
                            min={1}
                            max={60}
                            step={1}
                            className="mt-2"
                          />
                        </div>
                        
                        <div>
                          <Label htmlFor="ai-language">{t('home.language')}</Label>
                          <Select value={language} onValueChange={setLanguage}>
                            <SelectTrigger id="ai-language" data-testid="ai-language-select" className="mt-2">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="en-US">English (US)</SelectItem>
                              <SelectItem value="en-GB">English (UK)</SelectItem>
                              <SelectItem value="es-ES">Spanish</SelectItem>
                              <SelectItem value="fr-FR">French</SelectItem>
                              <SelectItem value="de-DE">German</SelectItem>
                              <SelectItem value="it-IT">Italian</SelectItem>
                              <SelectItem value="pt-BR">Portuguese (BR)</SelectItem>
                              <SelectItem value="ru-RU">Russian</SelectItem>
                              <SelectItem value="zh-CN">Chinese (Simplified)</SelectItem>
                              <SelectItem value="ja-JP">Japanese</SelectItem>
                              <SelectItem value="ar-SA">Arabic</SelectItem>
                              <SelectItem value="hi-IN">Hindi</SelectItem>
                              <SelectItem value="ko-KR">Korean</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                      
                      <Button 
                        onClick={handleGenerateText}
                        disabled={isGeneratingText}
                        className="w-full"
                        size="lg"
                        data-testid="generate-text-button"
                      >
                        {isGeneratingText ? (
                          <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            {t('aiGeneration.generatingText')}
                          </>
                        ) : (
                          <>
                            <Sparkles className="w-4 h-4 mr-2" />
                            {t('aiGeneration.generateText')}
                          </>
                        )}
                      </Button>
                      
                      {isGeneratingText && (
                        <div className="space-y-2">
                          <div className="flex justify-between text-sm">
                            <span className="text-muted-foreground">{textProgressMessage}</span>
                            <span className="font-medium">{textProgress}%</span>
                          </div>
                          <Progress value={textProgress} className="h-2" />
                        </div>
                      )}
                      
                      {generatedText && (
                        <div className="space-y-4">
                          <div>
                            <Label htmlFor="generated-text">{t('home.generatedTextEditable')}</Label>
                            <Textarea
                              id="generated-text"
                              data-testid="generated-text-display"
                              value={generatedText}
                              onChange={(e) => setGeneratedText(e.target.value)}
                              rows={12}
                              className="mt-2 font-mono text-sm"
                            />
                          </div>
                          
                          <Button 
                            onClick={() => handleSynthesize()}
                            disabled={isSynthesizing}
                            className="w-full"
                            size="lg"
                            data-testid="synthesize-ai-button"
                          >
                            {isSynthesizing ? (
                              <>
                                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                {t('aiGeneration.generatingAudio')}
                              </>
                            ) : (
                              <>
                                <Volume2 className="w-4 h-4 mr-2" />
                                {t('aiGeneration.synthesizeAudio')}
                              </>
                            )}
                          </Button>
                          
                          {isSynthesizing && (
                            <div className="space-y-3">
                              {/* Queue Status */}
                              {queuePosition > 0 && (
                                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-center">
                                  <p className="text-sm text-blue-700 font-medium">
                                    {t('home.inQueue')} {queuePosition}
                                  </p>
                                </div>
                              )}
                              
                              {/* Progress Bar */}
                              <div className="space-y-2">
                                <div className="flex justify-between text-sm items-center">
                                  <span className="text-muted-foreground font-medium">{audioProgressMessage}</span>
                                  <span className="font-bold text-primary">{audioProgress}%</span>
                                </div>
                                <Progress value={audioProgress} className="h-3" />
                              </div>
                              
                              {/* Detailed Stats */}
                              {audioStage === 'generating_segments' && totalSegments > 0 && (
                                <div className="grid grid-cols-2 gap-3 text-sm">
                                  <div className="bg-gray-50 rounded-lg p-2">
                                    <p className="text-xs text-gray-500">{t('home.progress')}</p>
                                    <p className="font-semibold text-gray-900">
                                      {completedSegments}/{totalSegments} {t('home.segments')}
                                    </p>
                                  </div>
                                  {audioEta && (
                                    <div className="bg-blue-50 rounded-lg p-2">
                                      <p className="text-xs text-blue-600">{t('home.remaining')}</p>
                                      <p className="font-semibold text-blue-900">{audioEta}</p>
                                    </div>
                                  )}
                                  {audioSpeed > 0 && (
                                    <div className="bg-green-50 rounded-lg p-2">
                                      <p className="text-xs text-green-600">{t('home.speed')}</p>
                                      <p className="font-semibold text-green-900">{audioSpeed.toFixed(1)}x</p>
                                    </div>
                                  )}
                                  {subscription?.tier === 'pro' && (
                                    <div className="bg-purple-50 rounded-lg p-2">
                                      <p className="text-xs text-purple-600">{t('home.status')}</p>
                                      <p className="font-semibold text-purple-900">{t('home.proPriority')}</p>
                                    </div>
                                  )}
                                </div>
                              )}
                              
                              {/* Stage Indicator */}
                              {audioStage && (
                                <div className="flex items-center justify-center gap-2 text-xs text-gray-500">
                                  {audioStage === 'loading_model' && `📥 ${t('progress.loadingModel')}`}
                                  {audioStage === 'generating_segments' && `🎙️ ${t('progress.generatingSegments')}`}
                                  {audioStage === 'combining' && `🔗 ${t('progress.combining')}`}
                                  {audioStage === 'saving' && `💾 ${t('progress.saving')}`}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </TabsContent>
                  
                  {/* Manual Input Tab */}
                  <TabsContent value="manual-input" className="space-y-6">
                    <div className="space-y-4">
                      <div>
                        <Label htmlFor="manual-text">{t('home.yourText')}</Label>
                        <Textarea
                          id="manual-text"
                          data-testid="manual-text-input"
                          placeholder={t('home.manualTextPlaceholder')}
                          value={manualText}
                          onChange={(e) => setManualText(e.target.value)}
                          rows={15}
                          className="mt-2 font-mono text-sm"
                        />
                      </div>
                      
                      <div>
                        <Label htmlFor="manual-language">{t('home.language')}</Label>
                        <Select value={language} onValueChange={setLanguage}>
                          <SelectTrigger id="manual-language" data-testid="manual-language-select" className="mt-2">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="en-US">English (US)</SelectItem>
                            <SelectItem value="en-GB">English (UK)</SelectItem>
                            <SelectItem value="es-ES">Spanish</SelectItem>
                            <SelectItem value="fr-FR">French</SelectItem>
                            <SelectItem value="de-DE">German</SelectItem>
                            <SelectItem value="it-IT">Italian</SelectItem>
                            <SelectItem value="pt-BR">Portuguese (BR)</SelectItem>
                            <SelectItem value="ru-RU">Russian</SelectItem>
                            <SelectItem value="zh-CN">Chinese (Simplified)</SelectItem>
                            <SelectItem value="ja-JP">Japanese</SelectItem>
                            <SelectItem value="ar-SA">Arabic</SelectItem>
                            <SelectItem value="hi-IN">Hindi</SelectItem>
                            <SelectItem value="ko-KR">Korean</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      
                      <Button 
                        onClick={() => handleSynthesize()}
                        disabled={isSynthesizing}
                        className="w-full"
                        size="lg"
                        data-testid="synthesize-manual-button"
                      >
                        {isSynthesizing ? (
                          <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            {t('manualInput.synthesizing')}
                          </>
                        ) : (
                          <>
                            <Volume2 className="w-4 h-4 mr-2" />
                            {t('manualInput.synthesize')}
                          </>
                        )}
                      </Button>
                      
                      {isSynthesizing && (
                        <div className="space-y-3 mt-4">
                          {/* Queue Status */}
                          {queuePosition > 0 && (
                            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-center">
                              <p className="text-sm text-blue-700 font-medium">
                                {t('home.inQueue')} {queuePosition}
                              </p>
                            </div>
                          )}
                          
                          {/* Progress Bar */}
                          <div className="space-y-2">
                            <div className="flex justify-between text-sm items-center">
                              <span className="text-muted-foreground font-medium">{audioProgressMessage}</span>
                              <span className="font-bold text-primary">{audioProgress}%</span>
                            </div>
                            <Progress value={audioProgress} className="h-3" />
                          </div>
                          
                          {/* Detailed Stats */}
                          {audioStage === 'generating_segments' && totalSegments > 0 && (
                            <div className="grid grid-cols-2 gap-3 text-sm">
                              <div className="bg-gray-50 rounded-lg p-2">
                                <p className="text-xs text-gray-500">{t('home.progress')}</p>
                                <p className="font-semibold text-gray-900">
                                  {completedSegments}/{totalSegments} {t('home.segments')}
                                </p>
                              </div>
                              {audioEta && (
                                <div className="bg-blue-50 rounded-lg p-2">
                                  <p className="text-xs text-blue-600">{t('home.remaining')}</p>
                                  <p className="font-semibold text-blue-900">{audioEta}</p>
                                </div>
                              )}
                              {audioSpeed > 0 && (
                                <div className="bg-green-50 rounded-lg p-2">
                                  <p className="text-xs text-green-600">{t('home.speed')}</p>
                                  <p className="font-semibold text-green-900">{audioSpeed.toFixed(1)}x</p>
                                </div>
                              )}
                              {subscription?.tier === 'pro' && (
                                <div className="bg-purple-50 rounded-lg p-2">
                                  <p className="text-xs text-purple-600">{t('home.status')}</p>
                                  <p className="font-semibold text-purple-900">{t('home.proPriority')}</p>
                                </div>
                              )}
                            </div>
                          )}
                          
                          {/* Stage Indicator */}
                          {audioStage && (
                            <div className="flex items-center justify-center gap-2 text-xs text-gray-500">
                              {audioStage === 'loading_model' && `📥 ${t('progress.loadingModel')}`}
                              {audioStage === 'generating_segments' && `🎙️ ${t('progress.generatingSegments')}`}
                              {audioStage === 'combining' && `🔗 ${t('progress.combining')}`}
                              {audioStage === 'saving' && `💾 ${t('progress.saving')}`}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          </div>
          
          {/* Settings Panel */}
          <div className="space-y-6">
            <Card className="backdrop-blur-sm bg-white/80 border-slate-200 shadow-xl" data-testid="settings-card">
              <CardHeader>
                <CardTitle>{t('home.voiceSettings')}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="language-setting">{t('home.language')}</Label>
                  <Select value={language} onValueChange={setLanguage}>
                    <SelectTrigger id="language-setting" data-testid="language-setting-select" className="mt-2">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="en-US">English (US)</SelectItem>
                      <SelectItem value="en-GB">English (UK)</SelectItem>
                      <SelectItem value="es-ES">Spanish</SelectItem>
                      <SelectItem value="fr-FR">French</SelectItem>
                      <SelectItem value="de-DE">German</SelectItem>
                      <SelectItem value="it-IT">Italian</SelectItem>
                      <SelectItem value="pt-BR">Portuguese (BR)</SelectItem>
                      <SelectItem value="ru-RU">Russian</SelectItem>
                      <SelectItem value="zh-CN">Chinese (Simplified)</SelectItem>
                      <SelectItem value="ja-JP">Japanese</SelectItem>
                      <SelectItem value="ar-SA">Arabic</SelectItem>
                      <SelectItem value="hi-IN">Hindi</SelectItem>
                      <SelectItem value="ko-KR">Korean</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                <div>
                  <Label htmlFor="voice">{t('voiceSettings.voice')}</Label>
                  <Select value={selectedVoice} onValueChange={setSelectedVoice}>
                    <SelectTrigger id="voice" data-testid="voice-select" className="mt-2">
                      <SelectValue placeholder={t('home.selectAVoice')} />
                    </SelectTrigger>
                    <SelectContent className="max-h-64">
                      {getVoicesByLanguage().map((voice) => (
                        <SelectItem key={voice.short_name} value={voice.short_name}>
                          {voice.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-slate-500 mt-1">{t('home.neuralTTSPowered')}</p>
                </div>
                
                <div>
                  <Label htmlFor="speed">
                    {t('home.speedLabel')}: {speed[0] > 0 ? '+' : ''}{speed[0]}% ({(1 + speed[0]/100).toFixed(1)}x)
                  </Label>
                  <Slider
                    id="speed"
                    data-testid="speed-slider"
                    value={speed}
                    onValueChange={setSpeed}
                    min={-50}
                    max={100}
                    step={10}
                    className="mt-2"
                  />
                  <p className="text-xs text-slate-500 mt-1">{t('home.adjustSpeed')}</p>
                </div>
              </CardContent>
            </Card>
            
            {/* Audio Player */}
            {audioUrl && (
              <Card className="backdrop-blur-sm bg-white/80 border-slate-200 shadow-xl" data-testid="audio-player-card">
                <CardHeader>
                  <CardTitle>{t('audioPlayer.title')}</CardTitle>
                  <div className="space-y-1 mt-2">
                    {audioDuration > 0 && (
                      <p className="text-sm text-slate-600">
                        {t('audioPlayer.duration')}: {Math.floor(audioDuration / 60)}:{String(Math.floor(audioDuration % 60)).padStart(2, '0')}
                      </p>
                    )}
                    {generationTime > 0 && (
                      <div className="flex gap-4 text-xs text-slate-500">
                        <span>⏱️ {t('progress.generationTime')}: {generationTime.toFixed(1)}с</span>
                        {audioSpeed > 0 && (
                          <span className="text-green-600 font-semibold">
                            ⚡ {t('progress.speed')}: {audioSpeed.toFixed(1)}x {t('progress.realTime')}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <audio controls className="w-full" data-testid="audio-player" key={audioUrl}>
                    <source src={audioUrl} type="audio/wav" />
                    <source src={audioUrl} type="audio/mpeg" />
                    {t('home.yourBrowserDoesNotSupport')}
                  </audio>
                  <div className="grid grid-cols-2 gap-2">
                    <a href={audioUrl} download className="w-full">
                      <Button className="w-full" variant="outline" data-testid="download-button">
                        <Download className="w-4 h-4 mr-2" />
                        {t('audioPlayer.downloadAudio')}
                      </Button>
                    </a>
                    <Button 
                      className="w-full" 
                      variant="outline"
                      onClick={() => currentAudioId && downloadText(currentAudioId)}
                      disabled={!currentAudioId}
                    >
                      📄 {t('audioPlayer.downloadText')}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}
            
            {/* Video Generation Section */}
            {audioUrl && (
              <Card className="backdrop-blur-sm bg-white/80 border-slate-200 shadow-xl">
                <CardHeader>
                  <CardTitle>🎬 {t('videoGeneration.createVideo')}</CardTitle>
                  <CardDescription>
                    {t('videoGeneration.description')}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label htmlFor="video-type">{t('videoGeneration.type')}</Label>
                    <Select value={videoType} onValueChange={setVideoType} disabled={isGeneratingVideo}>
                      <SelectTrigger id="video-type" className="mt-2">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="youtube_images">
                          {t('videoGeneration.youtubeImages')}
                        </SelectItem>
                        <SelectItem value="youtube_continuous">
                          {t('videoGeneration.youtubeContinuous')}
                        </SelectItem>
                        <SelectItem value="shorts">
                          {t('videoGeneration.shorts')}
                        </SelectItem>
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-slate-500 mt-2">
                      {videoType === "youtube_images" && t('videoGeneration.youtubeImagesDesc')}
                      {videoType === "youtube_continuous" && t('videoGeneration.youtubeContinuousDesc')}
                      {videoType === "shorts" && t('videoGeneration.shortsDesc')}
                    </p>
                  </div>
                  
                  {isGeneratingVideo && (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-slate-700">{videoProgressMessage}</span>
                        <span className="font-semibold text-blue-600">{videoProgress}%</span>
                      </div>
                      <Progress value={videoProgress} className="h-2" />
                      {videoStage && (
                        <p className="text-xs text-slate-600">
                          {t('videoGeneration.stage')}: {videoStage}
                        </p>
                      )}
                    </div>
                  )}
                  
                  <Button 
                    onClick={handleGenerateVideo}
                    disabled={isGeneratingVideo || !currentTextId || !currentAudioId}
                    className="w-full"
                    size="lg"
                  >
                    {isGeneratingVideo ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        {t('videoGeneration.generatingVideo')}
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-4 h-4 mr-2" />
                        {t('videoGeneration.createVideo')}
                      </>
                    )}
                  </Button>
                </CardContent>
              </Card>
            )}
            
            {/* Video Player */}
            {videoUrl && (
              <Card className="backdrop-blur-sm bg-white/80 border-slate-200 shadow-xl">
                <CardHeader>
                  <CardTitle>🎬 {t('videoGeneration.generatedVideo')}</CardTitle>
                  {videoDuration > 0 && (
                    <p className="text-sm text-slate-600">
                      {t('videoGeneration.duration')}: {Math.floor(videoDuration / 60)}:{String(Math.floor(videoDuration % 60)).padStart(2, '0')}
                    </p>
                  )}
                </CardHeader>
                <CardContent className="space-y-4">
                  <video controls className="w-full rounded-lg" key={videoUrl}>
                    <source src={videoUrl} type="video/mp4" />
                    Your browser does not support the video element.
                  </video>
                  <a href={videoUrl} download className="w-full">
                    <Button className="w-full" variant="outline">
                      <Download className="w-4 h-4 mr-2" />
                      {t('videoGeneration.downloadVideo')}
                    </Button>
                  </a>
                </CardContent>
              </Card>
            )}
            
            {/* History */}
            {history.length > 0 && (
              <Card className="backdrop-blur-sm bg-white/80 border-slate-200 shadow-xl" data-testid="history-card">
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span>{t('home.history')}</span>
                    <span className="text-xs text-slate-500">{t('home.filesStoredPermanently')}</span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {history.slice(0, 10).map((item) => (
                      <div key={item.id} className="p-3 bg-slate-50 rounded-lg border border-slate-200" data-testid={'history-item-' + item.id}>
                        <p className="text-sm text-slate-700 mb-2">{item.text}</p>
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-slate-500">{new Date(item.created_at).toLocaleString()}</span>
                          <div className="flex gap-2">
                            <Button 
                              size="sm" 
                              variant="ghost"
                              onClick={() => downloadText(item.id)}
                              title={t('audioPlayer.downloadText')}
                            >
                              📄
                            </Button>
                            <a href={API + item.audio_url} download>
                              <Button size="sm" variant="ghost" data-testid={'history-download-' + item.id} title={t('audioPlayer.downloadAudio')}>
                                <Download className="w-3 h-3" />
                              </Button>
                            </a>
                            <Button 
                              size="sm" 
                              variant="ghost"
                              onClick={() => deleteAudioFile(item.id)}
                              title={t('notifications.deleteFile')}
                              className="text-red-500 hover:text-red-700"
                            >
                              🗑️
                            </Button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
              {/* Video History */}
            {videoHistory.length > 0 && (
              <Card className="backdrop-blur-sm bg-white/80 border-slate-200 shadow-xl">
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span>🎬 {t('home.videoHistory')}</span>
                    <span className="text-xs text-slate-500">{videoHistory.length} {t('videoGeneration.videosCount')}</span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {videoHistory.slice(0, 10).map((video) => (
                      <div key={video.id} className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium text-slate-700">
                            {video.video_type === 'youtube_images' && t('videoGeneration.youtubeImagesShort')}
                            {video.video_type === 'youtube_continuous' && t('videoGeneration.youtubeContinuousShort')}
                            {video.video_type === 'shorts' && t('videoGeneration.shortsShort')}
                          </span>
                          {video.duration && (
                            <span className="text-xs text-slate-500">
                              {Math.floor(video.duration / 60)}:{String(Math.floor(video.duration % 60)).padStart(2, '0')}
                            </span>
                          )}
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-slate-500">{new Date(video.created_at).toLocaleString()}</span>
                          <div className="flex gap-2">
                            <Button 
                              size="sm" 
                              variant="ghost"
                              onClick={() => downloadVideo(video.id)}
                              title={t('videoGeneration.downloadVideo')}
                            >
                              🎬
                            </Button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
