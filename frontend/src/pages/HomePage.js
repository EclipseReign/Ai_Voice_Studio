import React, { useState, useEffect, useMemo, useCallback } from "react";
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
import { Loader2, Sparkles, Mic, Download, Clock, Volume2, User, LogOut, Wand2, LayoutGrid } from "lucide-react";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { ThemeSwitcher } from "@/components/ThemeSwitcher";
import Footer from "@/components/Footer";
import { VoiceSettingsSkeleton, HistorySkeleton } from "@/components/LoadingStates";
// Phase 1: New Components from Revid AI inspiration
import VideoWizard from "@/components/VideoWizard";
import TemplateLibrary from "@/components/TemplateLibrary";
import ViralHookGenerator from "@/components/ViralHookGenerator";
import DragDropUpload from "@/components/DragDropUpload";
import EnhancedProgress from "@/components/EnhancedProgress";

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
  
// Loading states for better UX
  const [isLoadingVoices, setIsLoadingVoices] = useState(true);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);

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
  
  const [subtitlesEnabled, setSubtitlesEnabled] = useState(false);
  const [subtitleStyle, setSubtitleStyle] = useState("tiktok");
  const [subtitlePosition, setSubtitlePosition] = useState("center");

  // Background video state (TikTok brainrot style)
  const [useBackgroundVideo, setUseBackgroundVideo] = useState(false);
  const [backgroundVideoType, setBackgroundVideoType] = useState("preset"); // "preset" or "upload"
  const [backgroundVideoPreset, setBackgroundVideoPreset] = useState("minecraft");
  const [presetBackgrounds, setPresetBackgrounds] = useState([]);
  const [uploadedBackgroundFile, setUploadedBackgroundFile] = useState(null);
  const [uploadedBackgroundFileId, setUploadedBackgroundFileId] = useState(null);
  const [isUploadingBackground, setIsUploadingBackground] = useState(false);

    // Phase 1: Mode and Wizard state
  const [uiMode, setUiMode] = useState("classic"); // "classic" or "wizard"
  const [wizardStep, setWizardStep] = useState(1);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [selectedHook, setSelectedHook] = useState("");

  const getVoicesByLanguage = useMemo(() => {
    const langCode = language.split('-')[0].toLowerCase();
    return voices.filter(v => v.locale.toLowerCase().startsWith(langCode));
  }, [language, voices]);

  // Fetch voices on mount
  useEffect(() => {
    fetchVoices();
    fetchHistory();
    fetchVideoHistory(); // Fetch video history on mount
    checkPendingJobs(); // NEW: Check for pending jobs on mount (recovery)
    fetchPresetBackgrounds(); // Fetch preset background videos
  }, []);
  
  // Update selected voice when language changes
  useEffect(() => {
    if (voices.length > 0 && getVoicesByLanguage.length > 0) {
      const currentVoiceInList = getVoicesByLanguage.find(v => v.short_name === selectedVoice);
      if (!currentVoiceInList) {
        setSelectedVoice(getVoicesByLanguage[0].short_name);
      }
    }
  }, [language, voices, getVoicesByLanguage, selectedVoice]);
  
  const fetchVoices = async () => {
    try {
      setIsLoadingVoices(true);
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
      } finally {
      setIsLoadingVoices(false);
    }
  };
  
  const fetchHistory = async () => {
    try {
      setIsLoadingHistory(true);
      const response = await axios.get(API + '/history', {
        withCredentials: true
      });
      setHistory(response.data);
    } catch (error) {
      console.error("Error fetching history:", error);
      toast.error(t('notifications.failedToLoadHistory'));
    } finally {
      setIsLoadingHistory(false);
    }
  };

  const fetchPresetBackgrounds = async () => {
    try {
      const response = await axios.get(API + '/video/preset-backgrounds', {
        withCredentials: true
      });
      setPresetBackgrounds(response.data.presets);
      if (response.data.presets.length > 0) {
        setBackgroundVideoPreset(response.data.presets[0].id);
      }
    } catch (error) {
      console.error("Error fetching preset backgrounds:", error);
      toast.error("Failed to load preset backgrounds");
    }
  };
  
  // Wrapper for DragDropUpload component
  const handleBackgroundVideoUploadDragDrop = async (file, error) => {
    if (error) {
      toast.error(error);
      return;
    }
    if (!file) return;
    
    // Call the original upload function with mock event
    await handleBackgroundVideoUploadOriginal(file);
  };

  const handleBackgroundVideoUpload = async (event) => {
      const file = event.target.files[0];
      if (!file) return;
      await handleBackgroundVideoUploadOriginal(file);
    };

  // Renamed original function
  const handleBackgroundVideoUploadOriginal = async (file) => {
    if (!file) return;
    
    // Validate file type
    const validTypes = ['video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/x-matroska'];
    if (!validTypes.includes(file.type) && !file.name.match(/.(mp4|mov|avi|mkv)$/i)) {
      toast.error("Please upload a valid video file (MP4, MOV, AVI, MKV)");
      return;
    }
    
    // Validate file size (max 500MB)
    const maxSize = 500 * 1024 * 1024; // 500MB
    if (file.size > maxSize) {
      toast.error("Video file is too large. Maximum size is 500MB.");
      return;
    }
    
    try {
      setIsUploadingBackground(true);
      setUploadedBackgroundFile(file);
      
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await axios.post(API + '/video/upload-background', formData, {
        withCredentials: true,
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          console.log(`Upload progress: ${percentCompleted}%`);
        }
      });
      
      setUploadedBackgroundFileId(response.data.file_id);
      toast.success("Background video uploaded successfully!");
      
    } catch (error) {
      console.error("Error uploading background video:", error);
      toast.error("Failed to upload background video. " + (error.response?.data?.detail || ""));
      setUploadedBackgroundFile(null);
      setUploadedBackgroundFileId(null);
    } finally {
      setIsUploadingBackground(false);
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
    // Validate background video settings if enabled
    if (useBackgroundVideo && videoType === 'shorts') {
      if (backgroundVideoType === 'upload' && !uploadedBackgroundFileId) {
        toast.error("Please upload a background video first");
        return;
      }
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
            video_type: videoType,
            subtitle_enabled: subtitlesEnabled,
            subtitle_style: subtitleStyle,
            subtitle_position: subtitlePosition,
            // Background video options (TikTok brainrot style)
            use_background_video: useBackgroundVideo,
            background_video_type: useBackgroundVideo ? backgroundVideoType : null,
            background_video_preset: (useBackgroundVideo && backgroundVideoType === 'preset') ? backgroundVideoPreset : null,
            background_video_file_id: (useBackgroundVideo && backgroundVideoType === 'upload') ? uploadedBackgroundFileId : null
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
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-slate-900 dark:to-slate-800">
      {/* Top Navigation Bar */}
      <div className="bg-white dark:bg-slate-900 shadow-sm border-b border-gray-200 dark:border-slate-700 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-3 sm:px-4 lg:px-8 py-2 sm:py-3">
          <div className="flex justify-between items-center gap-2">
            <div className="flex items-center space-x-2 sm:space-x-4 min-w-0">
              <h1 className="text-base sm:text-xl font-bold text-gray-900 dark:text-white whitespace-nowrap">🎙️ AI Voice Studio</h1>
              {subscription && (
                <div className="hidden md:flex items-center gap-3">
                  <span className={`px-2 sm:px-3 py-1 rounded-full text-xs font-semibold whitespace-nowrap ${
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

      <div className="max-w-7xl mx-auto p-3 sm:p-4 lg:p-6">
        {/* Header */}
        <div className="text-center mb-6 sm:mb-8 pt-2 sm:pt-4">
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold mb-2 sm:mb-3 bg-gradient-to-r from-blue-600 to-cyan-600 dark:from-blue-400 dark:to-cyan-400 bg-clip-text text-transparent" data-testid="main-heading">
          </h2>
          <p className="text-base sm:text-lg text-slate-600 dark:text-slate-300">{t('home.subtitle')}</p>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-4 sm:space-y-6 min-h-[600px]">
            <Card className="backdrop-blur-sm bg-white/80 border-slate-200 shadow-xl" data-testid="main-card">
              <CardHeader>
                <CardTitle className="text-xl sm:text-2xl">{t('home.createVoiceNarration')}</CardTitle>
                <CardDescription className="text-sm">{t('home.chooseGenerationMethod')}</CardDescription>
              </CardHeader>
              <CardContent>
                {/* Phase 1: Mode Switcher */}
                <div className="mb-6 p-4 bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 rounded-lg border border-purple-200 dark:border-purple-800">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <h3 className="text-sm font-semibold text-purple-900 dark:text-purple-100">
                        ✨ {t('modes.wizard')} - Новое!
                      </h3>
                      <p className="text-xs text-purple-700 dark:text-purple-300 mt-1">
                        {t('modes.wizardDesc')}
                      </p>
                    </div>
                    <Button
                      variant={uiMode === "wizard" ? "default" : "outline"}
                      size="sm"
                      onClick={() => setUiMode(uiMode === "classic" ? "wizard" : "classic")}
                      className={uiMode === "wizard" ? "bg-purple-600 hover:bg-purple-700" : ""}
                    >
                      {uiMode === "classic" ? (
                        <>
                          <Wand2 className="w-4 h-4 mr-2" />
                          {t('modes.wizard')}
                        </>
                      ) : (
                        <>
                          <LayoutGrid className="w-4 h-4 mr-2" />
                          {t('modes.classic')}
                        </>
                      )}
                    </Button>
                  </div>
                </div>

                {/* Classic Mode - Original Interface */}
                {uiMode === "classic" && (
                <Tabs value={activeTab} onValueChange={setActiveTab}>
                  <TabsList className="grid w-full grid-cols-2 mb-4 sm:mb-6 h-auto" data-testid="mode-tabs">
                    <TabsTrigger value="ai-generate" data-testid="ai-generate-tab" className="text-sm sm:text-base py-2">
                      <Sparkles className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2" />
                      <span className="hidden sm:inline">{t('home.aiGeneration')}</span>
                      <span className="sm:hidden">AI</span>
                    </TabsTrigger>
                    <TabsTrigger value="manual-input" data-testid="manual-input-tab" className="text-sm sm:text-base py-2">
                      <Mic className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2" />
                      <span className="hidden sm:inline">{t('home.manualInput')}</span>
                      <span className="sm:hidden">Manual</span>
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
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <Label htmlFor="duration" className="text-sm">
                            <Clock className="w-3 h-3 sm:w-4 sm:h-4 inline mr-1 sm:mr-2" />
                            {t('home.targetDuration')}: <span className="font-semibold">{duration}</span> {duration !== 1 ? t('home.minutes') : t('home.minute')}
                          </Label>
                          <div className="mt-2 px-1">
                            <Slider
                              id="duration"
                              data-testid="duration-slider"
                              value={[duration]}
                              onValueChange={(val) => setDuration(val[0])}
                              min={1}
                              max={60}
                              step={1}
                              className="touch-action-none"
                            />
                          </div>
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
                                <div className="grid grid-cols-2 gap-2 sm:gap-3 text-xs sm:text-sm">
                                  <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-2">
                                    <p className="text-xs text-gray-500 dark:text-gray-400">{t('home.progress')}</p>
                                    <p className="font-semibold text-gray-900 dark:text-gray-100 text-sm sm:text-base">
                                      {completedSegments}/{totalSegments} {t('home.segments')}
                                    </p>
                                  </div>
                                  {audioEta && (
                                    <div className="bg-blue-50 dark:bg-blue-900/30 rounded-lg p-2">
                                      <p className="text-xs text-blue-600 dark:text-blue-400">{t('home.remaining')}</p>
                                      <p className="font-semibold text-blue-900 dark:text-blue-100 text-sm sm:text-base">{audioEta}</p>
                                    </div>
                                  )}
                                  {audioSpeed > 0 && (
                                    <div className="bg-green-50 dark:bg-green-900/30 rounded-lg p-2">
                                      <p className="text-xs text-green-600 dark:text-green-400">{t('home.speed')}</p>
                                      <p className="font-semibold text-green-900 dark:text-green-100 text-sm sm:text-base">{audioSpeed.toFixed(1)}x</p>
                                    </div>
                                  )}
                                  {subscription?.tier === 'pro' && (
                                    <div className="bg-purple-50 dark:bg-purple-900/30 rounded-lg p-2">
                                      <p className="text-xs text-purple-600 dark:text-purple-400">{t('home.status')}</p>
                                      <p className="font-semibold text-purple-900 dark:text-purple-100 text-sm sm:text-base">{t('home.proPriority')}</p>
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
                )}

                {/* Wizard Mode - Step-by-step with templates and hooks */}
                {uiMode === "wizard" && (
                  <VideoWizard
                    currentStep={wizardStep}
                    onStepChange={setWizardStep}
                    canProceed={
                      (wizardStep === 1) || 
                      (wizardStep === 2 && (generatedText || manualText)) ||
                      (wizardStep === 3 && audioUrl) ||
                      (wizardStep === 4) ||
                      (wizardStep === 5 && videoUrl)
                    }
                    totalSteps={5}
                  >
                    {/* Step 1: Choose Method & Template */}
                    {wizardStep === 1 && (
                      <div className="space-y-6">
                        <TemplateLibrary
                          onSelectTemplate={(template) => {
                            setSelectedTemplate(template);
                            // Apply template settings
                            if (template.settings) {
                              setSubtitleStyle(template.settings.subtitle_style || "tiktok");
                              setSubtitlePosition(template.settings.subtitle_position || "center");
                              setVideoType(template.settings.video_type || "youtube_images");
                              setUseBackgroundVideo(template.settings.use_background || false);
                              if (template.settings.background_preset) {
                                setBackgroundVideoPreset(template.settings.background_preset);
                              }
                            }
                            toast.success(`Шаблон "${template.name}" применен!`);
                          }}
                        />
                        
                        <div className="mt-6">
                          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                            <TabsList className="grid w-full grid-cols-2">
                              <TabsTrigger value="ai-generate">
                                <Sparkles className="w-4 h-4 mr-2" />
                                {t('home.aiGeneration')}
                              </TabsTrigger>
                              <TabsTrigger value="manual-input">
                                <Mic className="w-4 h-4 mr-2" />
                                {t('home.manualInput')}
                              </TabsTrigger>
                            </TabsList>
                          </Tabs>
                        </div>
                      </div>
                    )}

                    {/* Step 2: Script Generation with Viral Hooks */}
                    {wizardStep === 2 && (
                      <div className="space-y-6">
                        {/* Viral Hook Generator */}
                        <ViralHookGenerator
                          onSelectHook={(hook) => {
                            setSelectedHook(hook);
                            // Prepend hook to prompt or manual text
                            if (activeTab === "ai-generate") {
                              setPrompt(hook + "\n\n" + prompt);
                            } else {
                              setManualText(hook + "\n\n" + manualText);
                            }
                            toast.success("Хук добавлен в начало текста!");
                          }}
                        />

                        {/* AI or Manual Input */}
                        {activeTab === "ai-generate" ? (
                          <div className="space-y-4">
                            <div>
                              <Label htmlFor="wizard-prompt">{t('home.topicPrompt')}</Label>
                              <Textarea
                                id="wizard-prompt"
                                placeholder={t('home.promptPlaceholderLong')}
                                value={prompt}
                                onChange={(e) => setPrompt(e.target.value)}
                                rows={4}
                                className="mt-2"
                              />
                            </div>
                            
                            <div className="grid grid-cols-2 gap-4">
                              <div>
                                <Label htmlFor="wizard-duration">
                                  <Clock className="w-4 h-4 inline mr-2" />
                                  {t('home.targetDuration')}: {duration} {t('home.minutes')}
                                </Label>
                                <Slider
                                  id="wizard-duration"
                                  value={[duration]}
                                  onValueChange={(val) => setDuration(val[0])}
                                  min={1}
                                  max={60}
                                  step={1}
                                  className="mt-2"
                                />
                              </div>
                              
                              <div>
                                <Label htmlFor="wizard-language">{t('home.language')}</Label>
                                <Select value={language} onValueChange={setLanguage}>
                                  <SelectTrigger id="wizard-language" className="mt-2">
                                    <SelectValue />
                                  </SelectTrigger>
                                  <SelectContent>
                                    <SelectItem value="ru-RU">🇷🇺 {t('languages.russian')}</SelectItem>
                                    <SelectItem value="en-US">🇺🇸 {t('languages.english')}</SelectItem>
                                    <SelectItem value="de-DE">🇩🇪 {t('languages.german')}</SelectItem>
                                    <SelectItem value="zh-CN">🇨🇳 {t('languages.chinese')}</SelectItem>
                                    <SelectItem value="it-IT">🇮🇹 {t('languages.italian')}</SelectItem>
                                    <SelectItem value="es-ES">🇪🇸 {t('languages.spanish')}</SelectItem>
                                    <SelectItem value="fr-FR">🇫🇷 {t('languages.french')}</SelectItem>
                                    <SelectItem value="pt-BR">🇧🇷 {t('languages.portuguese')}</SelectItem>
                                    <SelectItem value="ja-JP">🇯🇵 {t('languages.japanese')}</SelectItem>
                                    <SelectItem value="ko-KR">🇰🇷 {t('languages.korean')}</SelectItem>
                                  </SelectContent>
                                </Select>
                              </div>
                            </div>
                            
                            <Button
                              onClick={handleGenerateText}
                              disabled={isGeneratingText || !prompt.trim()}
                              className="w-full"
                              size="lg"
                            >
                              {isGeneratingText ? (
                                <>
                                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                  {t('aiGeneration.generatingText')}
                                </>
                              ) : (
                                <>
                                  <Sparkles className="mr-2 h-4 w-4" />
                                  {t('aiGeneration.generateText')}
                                </>
                              )}
                            </Button>
                            
                            {generatedText && (
                              <div className="mt-4">
                                <Label>{t('aiGeneration.editText')}</Label>
                                <Textarea
                                  value={generatedText}
                                  onChange={(e) => setGeneratedText(e.target.value)}
                                  rows={6}
                                  className="mt-2 font-mono text-sm"
                                />
                              </div>
                            )}
                          </div>
                        ) : (
                          <div className="space-y-4">
                            <div>
                              <Label htmlFor="wizard-manual-text">{t('manualInput.title')}</Label>
                              <Textarea
                                id="wizard-manual-text"
                                placeholder={t('manualInput.placeholder')}
                                value={manualText}
                                onChange={(e) => setManualText(e.target.value)}
                                rows={8}
                                className="mt-2"
                              />
                            </div>
                          </div>
                        )}

                        {/* Progress Display */}
                        {(isGeneratingText || textProgress > 0) && (
                          <EnhancedProgress
                            progress={textProgress}
                            message={textProgressMessage}
                            eta={audioEta}
                            speed={audioSpeed}
                            stage={audioStage || textProgressMessage}
                            completedSegments={completedSegments}
                            totalSegments={totalSegments}
                            queuePosition={queuePosition}
                            generationTime={generationTime}
                          />
                        )}
                      </div>
                    )}

                    {/* Step 3: Voice & Audio Generation */}
                    {wizardStep === 3 && (
                      <div className="space-y-6">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div>
                            <Label htmlFor="wizard-voice">{t('home.selectAVoice')}</Label>
                            <Select value={selectedVoice} onValueChange={setSelectedVoice}>
                              <SelectTrigger id="wizard-voice" className="mt-2">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent className="max-h-[200px]">
                                {getVoicesByLanguage.map((voice) => (
                                  <SelectItem key={voice.short_name} value={voice.short_name}>
                                    {voice.name}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                          
                          <div>
                            <Label htmlFor="wizard-speed">
                              {t('home.speedLabel')}: {(speed[0] / 50).toFixed(1)}x
                            </Label>
                            <Slider
                              id="wizard-speed"
                              value={speed}
                              onValueChange={setSpeed}
                              min={25}
                              max={100}
                              step={5}
                              className="mt-2"
                            />
                          </div>
                        </div>

                        <Button
                          onClick={handleSynthesize}
                          disabled={isSynthesizing || (!generatedText && !manualText) || !selectedVoice}
                          className="w-full"
                          size="lg"
                        >
                          {isSynthesizing ? (
                            <>
                              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                              {t('aiGeneration.generatingAudio')}
                            </>
                          ) : (
                            <>
                              <Volume2 className="mr-2 h-4 w-4" />
                              {t('aiGeneration.synthesizeAudio')}
                            </>
                          )}
                        </Button>

                        {/* Audio Progress */}
                        {(isSynthesizing || audioProgress > 0) && (
                          <EnhancedProgress
                            progress={audioProgress}
                            message={audioProgressMessage}
                            eta={audioEta}
                            speed={audioSpeed}
                            stage={audioStage}
                            completedSegments={completedSegments}
                            totalSegments={totalSegments}
                            queuePosition={queuePosition}
                            generationTime={generationTime}
                          />
                        )}

                        {/* Audio Player */}
                        {audioUrl && (
                          <Card className="bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20">
                            <CardContent className="pt-6">
                              <div className="flex items-center justify-between mb-3">
                                <span className="text-sm font-medium text-green-800 dark:text-green-200">
                                  ✅ {t('home.audioPlayer')}
                                </span>
                                <span className="text-xs text-green-600 dark:text-green-300">
                                  <Clock className="w-3 h-3 inline mr-1" />
                                  {Math.floor(audioDuration / 60)}:{String(Math.floor(audioDuration % 60)).padStart(2, '0')}
                                </span>
                              </div>
                              <audio controls src={audioUrl} className="w-full" />
                            </CardContent>
                          </Card>
                        )}
                      </div>
                    )}

                    {/* Step 4: Video Customization */}
                    {wizardStep === 4 && (
                      <div className="space-y-6">
                        <div className="space-y-4">
                          {/* Video Type */}
                          <div>
                            <Label htmlFor="wizard-video-type">{t('video.videoType')}</Label>
                            <Select value={videoType} onValueChange={setVideoType}>
                              <SelectTrigger id="wizard-video-type" className="mt-2">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="youtube_images">{t('video.aiGeneratedImages')}</SelectItem>
                                <SelectItem value="stock">{t('video.stockFootage')}</SelectItem>
                                <SelectItem value="upload">{t('video.uploadOwn')}</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>

                          {/* Subtitles */}
                          <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-slate-800 rounded-lg">
                            <div>
                              <Label>{t('video.subtitles')}</Label>
                              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                                {t('video.subtitlesDesc')}
                              </p>
                            </div>
                            <Button
                              variant={subtitlesEnabled ? "default" : "outline"}
                              size="sm"
                              onClick={() => setSubtitlesEnabled(!subtitlesEnabled)}
                            >
                              {subtitlesEnabled ? t('common.on') : t('common.off')}
                            </Button>
                          </div>

                          {subtitlesEnabled && (
                            <div className="grid grid-cols-2 gap-4">
                              <div>
                                <Label>{t('video.subtitleStyle')}</Label>
                                <Select value={subtitleStyle} onValueChange={setSubtitleStyle}>
                                  <SelectTrigger className="mt-2">
                                    <SelectValue />
                                  </SelectTrigger>
                                  <SelectContent>
                                    <SelectItem value="tiktok">TikTok Style</SelectItem>
                                    <SelectItem value="youtube">YouTube Style</SelectItem>
                                    <SelectItem value="instagram">Instagram Style</SelectItem>
                                    <SelectItem value="podcast">Podcast Style</SelectItem>
                                  </SelectContent>
                                </Select>
                              </div>
                              
                              <div>
                                <Label>{t('video.subtitlePosition')}</Label>
                                <Select value={subtitlePosition} onValueChange={setSubtitlePosition}>
                                  <SelectTrigger className="mt-2">
                                    <SelectValue />
                                  </SelectTrigger>
                                  <SelectContent>
                                    <SelectItem value="top">{t('video.top')}</SelectItem>
                                    <SelectItem value="center">{t('video.center')}</SelectItem>
                                    <SelectItem value="bottom">{t('video.bottom')}</SelectItem>
                                  </SelectContent>
                                </Select>
                              </div>
                            </div>
                          )}

                          {/* Background Video */}
                          <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-slate-800 rounded-lg">
                            <div>
                              <Label>{t('video.backgroundVideo')}</Label>
                              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                                {t('video.backgroundVideoDesc')}
                              </p>
                            </div>
                            <Button
                              variant={useBackgroundVideo ? "default" : "outline"}
                              size="sm"
                              onClick={() => setUseBackgroundVideo(!useBackgroundVideo)}
                            >
                              {useBackgroundVideo ? t('common.on') : t('common.off')}
                            </Button>
                          </div>

                          {useBackgroundVideo && (
                            <div className="space-y-4">
                              <Tabs value={backgroundVideoType} onValueChange={setBackgroundVideoType}>
                                <TabsList className="grid w-full grid-cols-2">
                                  <TabsTrigger value="preset">{t('video.presetBackgrounds')}</TabsTrigger>
                                  <TabsTrigger value="upload">{t('video.uploadCustom')}</TabsTrigger>
                                </TabsList>
                                
                                <TabsContent value="preset" className="mt-4">
                                  <Select value={backgroundVideoPreset} onValueChange={setBackgroundVideoPreset}>
                                    <SelectTrigger>
                                      <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                      {presetBackgrounds.map((preset) => (
                                        <SelectItem key={preset.id} value={preset.id}>
                                          {preset.name}
                                        </SelectItem>
                                      ))}
                                    </SelectContent>
                                  </Select>
                                </TabsContent>
                                
                                <TabsContent value="upload" className="mt-4">
                                  <DragDropUpload
                                    onFileSelect={handleBackgroundVideoUploadDragDrop}
                                    acceptedFileTypes={{ 'video/*': ['.mp4', '.mov', '.avi', '.mkv'] }}
                                    maxSize={500 * 1024 * 1024}
                                    isUploading={isUploadingBackground}
                                  />
                                </TabsContent>
                              </Tabs>
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Step 5: Preview & Generate */}
                    {wizardStep === 5 && (
                      <div className="space-y-6">
                        <div className="text-center">
                          <h3 className="text-lg font-semibold mb-2">{t('wizard.step5')}</h3>
                          <p className="text-sm text-gray-600 dark:text-gray-400">
                            {t('wizard.step5Desc')}
                          </p>
                        </div>

                        <Button
                          onClick={handleGenerateVideo}
                          disabled={isGeneratingVideo || !audioUrl}
                          className="w-full"
                          size="lg"
                        >
                          {isGeneratingVideo ? (
                            <>
                              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                              {t('video.generatingVideo')}
                            </>
                          ) : (
                            <>
                              <Sparkles className="mr-2 h-4 w-4" />
                              {t('video.generateVideo')}
                            </>
                          )}
                        </Button>

                        {/* Video Progress */}
                        {(isGeneratingVideo || videoProgress > 0) && (
                          <EnhancedProgress
                            progress={videoProgress}
                            message={videoProgressMessage}
                            eta=""
                            speed={0}
                            stage={videoStage}
                            completedSegments={0}
                            totalSegments={0}
                            queuePosition={0}
                            generationTime={0}
                          />
                        )}

                        {/* Video Player */}
                        {videoUrl && (
                          <Card className="bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20">
                            <CardContent className="pt-6">
                              <div className="flex items-center justify-between mb-3">
                                <span className="text-sm font-medium text-purple-800 dark:text-purple-200">
                                  ✅ {t('video.videoReady')}
                                </span>
                                <Button
                                  onClick={() => downloadVideo(currentVideoId)}
                                  size="sm"
                                  variant="outline"
                                >
                                  <Download className="w-4 h-4 mr-2" />
                                  {t('video.download')}
                                </Button>
                              </div>
                              <video controls src={videoUrl} className="w-full rounded-lg" />
                            </CardContent>
                          </Card>
                        )}
                      </div>
                    )}
                  </VideoWizard>
                )}
              </CardContent>
            </Card>
          </div>
          
          {/* Settings Panel */}
          <div className="space-y-4 sm:space-y-6">
            {isLoadingVoices ? (
              <VoiceSettingsSkeleton />
            ) : (
              <Card className="backdrop-blur-sm bg-white/80 border-slate-200 shadow-xl" data-testid="settings-card">
                <CardHeader>
                  <CardTitle className="text-lg sm:text-xl">{t('home.voiceSettings')}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label htmlFor="language-setting" className="text-sm">{t('home.language')}</Label>
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
                    <Label htmlFor="voice" className="text-sm">{t('voiceSettings.voice')}</Label>
                    <Select value={selectedVoice} onValueChange={setSelectedVoice}>
                      <SelectTrigger id="voice" data-testid="voice-select" className="mt-2">
                        <SelectValue placeholder={t('home.selectAVoice')} />
                      </SelectTrigger>
                      <SelectContent className="max-h-64">
                        {getVoicesByLanguage.map((voice) => (
                          <SelectItem key={voice.short_name} value={voice.short_name}>
                            {voice.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-slate-500 mt-1">{t('home.neuralTTSPowered')}</p>
                  </div>
                  
                  <div>
                    <Label htmlFor="speed" className="text-sm">
                      {t('home.speedLabel')}: {speed[0] > 0 ? '+' : ''}{speed[0]}% ({(1 + speed[0]/100).toFixed(1)}x)
                    </Label>
                    <div className="mt-2 px-1">
                      <Slider
                        id="speed"
                        data-testid="speed-slider"
                        value={speed}
                        onValueChange={setSpeed}
                        min={-50}
                        max={100}
                        step={10}
                        className="touch-action-none"
                      />
                    </div>
                    <p className="text-xs text-slate-500 mt-1">{t('home.adjustSpeed')}</p>
                  </div>
                </CardContent>
              </Card>
            )}
            {/* Audio Player */}
            {audioUrl && (
              <Card className="backdrop-blur-sm bg-white/80 border-slate-200 shadow-xl min-h-[180px]" data-testid="audio-player-card">
                <CardHeader>
                  <CardTitle className="text-lg sm:text-xl">{t('audioPlayer.title')}</CardTitle>
                  <div className="space-y-1 mt-2">
                    {audioDuration > 0 && (
                      <p className="text-sm text-slate-600 dark:text-slate-400">
                        {t('audioPlayer.duration')}: {Math.floor(audioDuration / 60)}:{String(Math.floor(audioDuration % 60)).padStart(2, '0')}
                      </p>
                    )}
                    {generationTime > 0 && (
                      <div className="flex flex-wrap gap-2 sm:gap-4 text-xs text-slate-500 dark:text-slate-400">
                        <span>⏱️ {t('progress.generationTime')}: {generationTime.toFixed(1)}с</span>
                        {audioSpeed > 0 && (
                          <span className="text-green-600 dark:text-green-400 font-semibold">
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
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    <a href={audioUrl} download className="w-full">
                      <Button className="w-full text-sm" variant="outline" data-testid="download-button">
                        <Download className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2" />
                        {t('audioPlayer.downloadAudio')}
                      </Button>
                    </a>
                    <Button 
                      className="w-full text-sm" 
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
                  {/* Subtitle Settings */}
                  <div className="space-y-4 p-4 bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 rounded-lg border border-purple-200 dark:border-purple-800">
                    <div className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        id="enable-subtitles"
                        checked={subtitlesEnabled}
                        onChange={(e) => setSubtitlesEnabled(e.target.checked)}
                        disabled={isGeneratingVideo}
                        className="w-4 h-4 text-purple-600 bg-gray-100 border-gray-300 rounded focus:ring-purple-500 dark:focus:ring-purple-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
                      />
                      <Label htmlFor="enable-subtitles" className="text-sm font-medium cursor-pointer">
                        💬 {t('videoGeneration.enableSubtitles')}
                      </Label>
                    </div>
                    
                    {subtitlesEnabled && (
                      <div className="space-y-3 ml-6 animate-in slide-in-from-top-2 duration-300">
                        {/* Subtitle Style */}
                        <div>
                          <Label htmlFor="subtitle-style" className="text-sm">
                            {t('videoGeneration.subtitleStyle')}
                          </Label>
                          <Select value={subtitleStyle} onValueChange={setSubtitleStyle} disabled={isGeneratingVideo}>
                            <SelectTrigger id="subtitle-style" className="mt-1.5 bg-white dark:bg-slate-800">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="tiktok">
                                <div className="flex items-center gap-2">
                                  <span className="text-lg">🎵</span>
                                  <span>{t('videoGeneration.tiktokStyle')}</span>
                                </div>
                              </SelectItem>
                              <SelectItem value="instagram">
                                <div className="flex items-center gap-2">
                                  <span className="text-lg">📸</span>
                                  <span>{t('videoGeneration.instagramStyle')}</span>
                                </div>
                              </SelectItem>
                              <SelectItem value="minimal">
                                <div className="flex items-center gap-2">
                                  <span className="text-lg">✨</span>
                                  <span>{t('videoGeneration.minimalStyle')}</span>
                                </div>
                              </SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        
                        {/* Subtitle Position */}
                        <div>
                          <Label className="text-sm mb-2 block">
                            {t('videoGeneration.subtitlePosition')}
                          </Label>
                          <div className="flex gap-2">
                            <button
                              type="button"
                              onClick={() => setSubtitlePosition("center")}
                              disabled={isGeneratingVideo}
                              className={`flex-1 px-3 py-2 text-sm rounded-md border transition-all ${
                                subtitlePosition === "center"
                                  ? 'bg-purple-600 text-white border-purple-600 shadow-md'
                                  : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-300 dark:border-slate-600 hover:border-purple-400'
                              } ${isGeneratingVideo ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                            >
                              ⬆️ {t('videoGeneration.centerPosition')}
                            </button>
                            <button
                              type="button"
                              onClick={() => setSubtitlePosition("bottom")}
                              disabled={isGeneratingVideo}
                              className={`flex-1 px-3 py-2 text-sm rounded-md border transition-all ${
                                subtitlePosition === "bottom"
                                  ? 'bg-purple-600 text-white border-purple-600 shadow-md'
                                  : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-300 dark:border-slate-600 hover:border-purple-400'
                              } ${isGeneratingVideo ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                            >
                              ⬇️ {t('videoGeneration.bottomPosition')}
                            </button>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Background Video Settings (TikTok Brainrot Style) - Only for Shorts */}
                  {videoType === "shorts" && (
                    <div className="space-y-4 p-4 bg-gradient-to-r from-blue-50 to-cyan-50 dark:from-blue-900/20 dark:to-cyan-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                      <div className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          id="enable-background-video"
                          checked={useBackgroundVideo}
                          onChange={(e) => setUseBackgroundVideo(e.target.checked)}
                          disabled={isGeneratingVideo}
                          className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
                        />
                        <Label htmlFor="enable-background-video" className="text-sm font-medium cursor-pointer">
                          🎮 Use Background Video (TikTok Style)
                        </Label>
                      </div>
                      
                      {useBackgroundVideo && (
                        <div className="space-y-3 ml-6 animate-in slide-in-from-top-2 duration-300">
                          {/* Video Type Selection */}
                          <div>
                            <Label className="text-sm mb-2 block">
                              Video Source
                            </Label>
                            <div className="flex gap-2">
                              <button
                                type="button"
                                onClick={() => setBackgroundVideoType("preset")}
                                disabled={isGeneratingVideo}
                                className={`flex-1 px-3 py-2 text-sm rounded-md border transition-all ${
                                  backgroundVideoType === "preset"
                                    ? 'bg-blue-600 text-white border-blue-600 shadow-md'
                                    : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-300 dark:border-slate-600 hover:border-blue-400'
                                } ${isGeneratingVideo ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                              >
                                📦 Preset
                              </button>
                              <button
                                type="button"
                                onClick={() => setBackgroundVideoType("upload")}
                                disabled={isGeneratingVideo}
                                className={`flex-1 px-3 py-2 text-sm rounded-md border transition-all ${
                                  backgroundVideoType === "upload"
                                    ? 'bg-blue-600 text-white border-blue-600 shadow-md'
                                    : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-300 dark:border-slate-600 hover:border-blue-400'
                                } ${isGeneratingVideo ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                              >
                                ⬆️ Upload
                              </button>
                            </div>
                          </div>
                          
                          {/* Preset Selection */}
                          {backgroundVideoType === "preset" && (
                            <div className="space-y-2">
                              <Label className="text-sm">Choose Background</Label>
                              <div className="grid grid-cols-2 gap-2">
                                {presetBackgrounds.map((preset) => (
                                  <button
                                    key={preset.id}
                                    type="button"
                                    onClick={() => setBackgroundVideoPreset(preset.id)}
                                    disabled={isGeneratingVideo}
                                    className={`relative p-2 rounded-lg border-2 transition-all ${
                                      backgroundVideoPreset === preset.id
                                        ? 'border-blue-600 bg-blue-50 dark:bg-blue-900/30'
                                        : 'border-slate-200 dark:border-slate-700 hover:border-blue-400'
                                    } ${isGeneratingVideo ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                                  >
                                    <div className="aspect-video bg-slate-200 dark:bg-slate-700 rounded mb-2 overflow-hidden">
                                      <img 
                                        src={preset.thumbnail} 
                                        alt={preset.name}
                                        className="w-full h-full object-cover"
                                      />
                                    </div>
                                    <p className="text-xs font-medium text-center">{preset.name}</p>
                                    {backgroundVideoPreset === preset.id && (
                                      <div className="absolute top-1 right-1 bg-blue-600 text-white rounded-full w-5 h-5 flex items-center justify-center">
                                        ✓
                                      </div>
                                    )}
                                  </button>
                                ))}
                              </div>
                            </div>
                          )}
                          
                          {/* Upload Option */}
                          {backgroundVideoType === "upload" && (
                            <div className="space-y-2">
                              <Label htmlFor="bg-video-upload" className="text-sm">
                                Upload Your Video
                              </Label>
                              <input
                                type="file"
                                id="bg-video-upload"
                                accept="video/*"
                                onChange={handleBackgroundVideoUpload}
                                disabled={isGeneratingVideo || isUploadingBackground}
                                className="block w-full text-sm text-slate-500
                                  file:mr-4 file:py-2 file:px-4
                                  file:rounded-md file:border-0
                                  file:text-sm file:font-semibold
                                  file:bg-blue-50 file:text-blue-700
                                  hover:file:bg-blue-100
                                  dark:file:bg-blue-900 dark:file:text-blue-300
                                  disabled:opacity-50 disabled:cursor-not-allowed"
                              />
                              {isUploadingBackground && (
                                <p className="text-xs text-blue-600">
                                  <Loader2 className="inline w-3 h-3 animate-spin mr-1" />
                                  Uploading video...
                                </p>
                              )}
                              {uploadedBackgroundFile && !isUploadingBackground && (
                                <p className="text-xs text-green-600">
                                  ✓ {uploadedBackgroundFile.name} uploaded
                                </p>
                              )}
                              <p className="text-xs text-slate-500">
                                Max 500MB • MP4, MOV, AVI, MKV
                              </p>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}

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
            {isLoadingHistory ? (
              <HistorySkeleton />
            ) : history.length > 0 && (
              <Card className="backdrop-blur-sm bg-white/80 border-slate-200 shadow-xl min-h-[200px]" data-testid="history-card">
                <CardHeader>
                  <CardTitle className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
                    <span className="text-lg sm:text-xl">{t('home.history')}</span>
                    <span className="text-xs text-slate-500">{t('home.filesStoredPermanently')}</span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {history.slice(0, 10).map((item) => (
                      <div key={item.id} className="p-2 sm:p-3 bg-slate-50 dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700" data-testid={'history-item-' + item.id}>
                        <p className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 mb-2 line-clamp-2">{item.text}</p>
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-xs text-slate-500 dark:text-slate-400">{new Date(item.created_at).toLocaleString()}</span>
                          <div className="flex gap-1 sm:gap-2">
                            <Button 
                              size="sm" 
                              variant="ghost"
                              onClick={() => downloadText(item.id)}
                              title={t('audioPlayer.downloadText')}
                              className="h-8 w-8 p-0"
                            >
                              📄
                            </Button>
                            <a href={API + item.audio_url} download>
                              <Button size="sm" variant="ghost" data-testid={'history-download-' + item.id} title={t('audioPlayer.downloadAudio')} className="h-8 w-8 p-0">
                                <Download className="w-3 h-3" />
                              </Button>
                            </a>
                            <Button 
                              size="sm" 
                              variant="ghost"
                              onClick={() => deleteAudioFile(item.id)}
                              title={t('notifications.deleteFile')}
                              className="text-red-500 hover:text-red-700 h-8 w-8 p-0"
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
      {/* Footer */}
      <Footer />
    </div>
  );
};

export default HomePage;
