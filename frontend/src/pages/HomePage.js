import React, { useState, useEffect } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
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

const HomePage = () => {
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
  const [history, setHistory] = useState([]);
  
  // Fetch voices on mount
  useEffect(() => {
    fetchVoices();
    fetchHistory();
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
      toast.error("Не удалось загрузить голоса");
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
  
  const handleGenerateText = async () => {
    if (!prompt.trim()) {
      toast.error("Пожалуйста, введите промпт");
      return;
    }
    
    setIsGeneratingText(true);
    setTextProgress(0);
    setTextProgressMessage("Начало генерации...");
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
                setTextProgressMessage("Готово!");
                setGeneratedText(data.text);
                toast.success(`Сгенерировано ${data.word_count} слов!`);
                setIsGeneratingText(false);
                // Refresh subscription to update usage count
                await refreshSubscription();
              } else if (data.type === 'error') {
                toast.error(data.message || "Ошибка генерации текста");
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
      toast.error("Не удалось сгенерировать текст");
      setIsGeneratingText(false);
    }
  };
  
  const handleSynthesize = async (text) => {
    if (!text.trim()) {
      toast.error("Пожалуйста, введите текст для озвучки");
      return;
    }
    
    if (!selectedVoice) {
      toast.error("Пожалуйста, выберите голос");
      return;
    }
    
    setIsSynthesizing(true);
    setAudioProgress(0);
    setAudioProgressMessage("Подготовка...");
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
                setAudioProgressMessage(data.message || "Готово!");
                setAudioUrl(API + data.audio_url);
                setAudioDuration(data.duration || 0);
                setGenerationTime(data.generation_time || 0);
                if (data.speed) {
                  setAudioSpeed(data.speed);
                }
                toast.success(data.message || "Аудио успешно сгенерировано!");
                fetchHistory();
                setIsSynthesizing(false);
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
      toast.error("Не удалось сгенерировать аудио");
      setIsSynthesizing(false);
    }
  };
  
  const getVoicesByLanguage = () => {
    const langCode = language.split('-')[0].toLowerCase();
    return voices.filter(v => v.locale.toLowerCase().startsWith(langCode));
  };
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Top Navigation Bar */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-4">
              <h1 className="text-xl font-bold text-gray-900">🎙️ AI Voice Studio</h1>
              {subscription && (
                <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                  subscription.tier === 'pro'
                    ? 'bg-gradient-to-r from-purple-100 to-pink-100 text-purple-800 border border-purple-200'
                    : 'bg-gray-100 text-gray-700'
                }`}>
                  {subscription.tier === 'pro' ? '✨ Pro' : `Free (${subscription.usage_today || 0}/3)`}
                </span>
              )}
            </div>
            <div className="flex items-center space-x-3">
              <button
                onClick={() => navigate('/dashboard')}
                className="flex items-center space-x-2 px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
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
          <h2 className="text-4xl lg:text-5xl font-bold mb-3 bg-gradient-to-r from-blue-600 to-cyan-600 bg-clip-text text-transparent" data-testid="main-heading">
            Генерация и Озвучка
          </h2>
          <p className="text-lg text-slate-600">Создавайте тексты с помощью ИИ и озвучивайте их реалистичными голосами</p>
        </div>
        
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2">
            <Card className="backdrop-blur-sm bg-white/80 border-slate-200 shadow-xl" data-testid="main-card">
              <CardHeader>
                <CardTitle className="text-2xl">Create Voice Narration</CardTitle>
                <CardDescription>Choose your generation method</CardDescription>
              </CardHeader>
              <CardContent>
                <Tabs value={activeTab} onValueChange={setActiveTab}>
                  <TabsList className="grid w-full grid-cols-2 mb-6" data-testid="mode-tabs">
                    <TabsTrigger value="ai-generate" data-testid="ai-generate-tab">
                      <Sparkles className="w-4 h-4 mr-2" />
                      AI Generate
                    </TabsTrigger>
                    <TabsTrigger value="manual-input" data-testid="manual-input-tab">
                      <Mic className="w-4 h-4 mr-2" />
                      Manual Input
                    </TabsTrigger>
                  </TabsList>
                  
                  {/* AI Generate Tab */}
                  <TabsContent value="ai-generate" className="space-y-6">
                    <div className="space-y-4">
                      <div>
                        <Label htmlFor="prompt">Topic / Prompt</Label>
                        <Textarea
                          id="prompt"
                          data-testid="ai-prompt-input"
                          placeholder="Enter a topic or prompt for text generation (e.g., 'The history of artificial intelligence')"
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
                            Target Duration: {duration} minute{duration !== 1 ? 's' : ''}
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
                          <Label htmlFor="ai-language">Language</Label>
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
                            Генерация текста...
                          </>
                        ) : (
                          <>
                            <Sparkles className="w-4 h-4 mr-2" />
                            Сгенерировать текст
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
                            <Label htmlFor="generated-text">Generated Text (editable)</Label>
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
                            onClick={() => handleSynthesize(generatedText)}
                            disabled={isSynthesizing}
                            className="w-full"
                            size="lg"
                            data-testid="synthesize-ai-button"
                          >
                            {isSynthesizing ? (
                              <>
                                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                Генерация аудио...
                              </>
                            ) : (
                              <>
                                <Volume2 className="w-4 h-4 mr-2" />
                                Озвучить текст
                              </>
                            )}
                          </Button>
                          
                          {isSynthesizing && (
                            <div className="space-y-3">
                              {/* Queue Status */}
                              {queuePosition > 0 && (
                                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-center">
                                  <p className="text-sm text-blue-700 font-medium">
                                    В очереди - позиция {queuePosition}
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
                                    <p className="text-xs text-gray-500">Прогресс</p>
                                    <p className="font-semibold text-gray-900">
                                      {completedSegments}/{totalSegments} сегментов
                                    </p>
                                  </div>
                                  {audioEta && (
                                    <div className="bg-blue-50 rounded-lg p-2">
                                      <p className="text-xs text-blue-600">Осталось</p>
                                      <p className="font-semibold text-blue-900">{audioEta}</p>
                                    </div>
                                  )}
                                  {audioSpeed > 0 && (
                                    <div className="bg-green-50 rounded-lg p-2">
                                      <p className="text-xs text-green-600">Скорость</p>
                                      <p className="font-semibold text-green-900">{audioSpeed.toFixed(1)}x</p>
                                    </div>
                                  )}
                                  {subscription?.tier === 'pro' && (
                                    <div className="bg-purple-50 rounded-lg p-2">
                                      <p className="text-xs text-purple-600">Статус</p>
                                      <p className="font-semibold text-purple-900">⚡ Pro Priority</p>
                                    </div>
                                  )}
                                </div>
                              )}
                              
                              {/* Stage Indicator */}
                              {audioStage && (
                                <div className="flex items-center justify-center gap-2 text-xs text-gray-500">
                                  {audioStage === 'loading_model' && '📥 Загрузка модели'}
                                  {audioStage === 'generating_segments' && '🎙️ Генерация аудио'}
                                  {audioStage === 'combining' && '🔗 Объединение сегментов'}
                                  {audioStage === 'saving' && '💾 Сохранение файла'}
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
                        <Label htmlFor="manual-text">Your Text</Label>
                        <Textarea
                          id="manual-text"
                          data-testid="manual-text-input"
                          placeholder="Paste or type your text here..."
                          value={manualText}
                          onChange={(e) => setManualText(e.target.value)}
                          rows={15}
                          className="mt-2 font-mono text-sm"
                        />
                      </div>
                      
                      <div>
                        <Label htmlFor="manual-language">Language</Label>
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
                        onClick={() => handleSynthesize(manualText)}
                        disabled={isSynthesizing}
                        className="w-full"
                        size="lg"
                        data-testid="synthesize-manual-button"
                      >
                        {isSynthesizing ? (
                          <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            Генерация аудио...
                          </>
                        ) : (
                          <>
                            <Volume2 className="w-4 h-4 mr-2" />
                            Озвучить текст
                          </>
                        )}
                      </Button>
                      
                      {isSynthesizing && (
                        <div className="space-y-3 mt-4">
                          {/* Queue Status */}
                          {queuePosition > 0 && (
                            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-center">
                              <p className="text-sm text-blue-700 font-medium">
                                В очереди - позиция {queuePosition}
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
                                <p className="text-xs text-gray-500">Прогресс</p>
                                <p className="font-semibold text-gray-900">
                                  {completedSegments}/{totalSegments} сегментов
                                </p>
                              </div>
                              {audioEta && (
                                <div className="bg-blue-50 rounded-lg p-2">
                                  <p className="text-xs text-blue-600">Осталось</p>
                                  <p className="font-semibold text-blue-900">{audioEta}</p>
                                </div>
                              )}
                              {audioSpeed > 0 && (
                                <div className="bg-green-50 rounded-lg p-2">
                                  <p className="text-xs text-green-600">Скорость</p>
                                  <p className="font-semibold text-green-900">{audioSpeed.toFixed(1)}x</p>
                                </div>
                              )}
                              {subscription?.tier === 'pro' && (
                                <div className="bg-purple-50 rounded-lg p-2">
                                  <p className="text-xs text-purple-600">Статус</p>
                                  <p className="font-semibold text-purple-900">⚡ Pro Priority</p>
                                </div>
                              )}
                            </div>
                          )}
                          
                          {/* Stage Indicator */}
                          {audioStage && (
                            <div className="flex items-center justify-center gap-2 text-xs text-gray-500">
                              {audioStage === 'loading_model' && '📥 Загрузка модели'}
                              {audioStage === 'generating_segments' && '🎙️ Генерация аудио'}
                              {audioStage === 'combining' && '🔗 Объединение сегментов'}
                              {audioStage === 'saving' && '💾 Сохранение файла'}
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
                <CardTitle>Voice Settings</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="language-setting">Language</Label>
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
                  <Label htmlFor="voice">Voice</Label>
                  <Select value={selectedVoice} onValueChange={setSelectedVoice}>
                    <SelectTrigger id="voice" data-testid="voice-select" className="mt-2">
                      <SelectValue placeholder="Select a voice" />
                    </SelectTrigger>
                    <SelectContent className="max-h-64">
                      {getVoicesByLanguage().map((voice) => (
                        <SelectItem key={voice.short_name} value={voice.short_name}>
                          {voice.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-slate-500 mt-1">Neural TTS voices powered by Piper</p>
                </div>
                
                <div>
                  <Label htmlFor="speed">
                    Speed: {speed[0] > 0 ? '+' : ''}{speed[0]}% ({(1 + speed[0]/100).toFixed(1)}x)
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
                  <p className="text-xs text-slate-500 mt-1">Adjust speech speed (0.5x to 2.0x)</p>
                </div>
              </CardContent>
            </Card>
            
            {/* Audio Player */}
            {audioUrl && (
              <Card className="backdrop-blur-sm bg-white/80 border-slate-200 shadow-xl" data-testid="audio-player-card">
                <CardHeader>
                  <CardTitle>Generated Audio</CardTitle>
                  <div className="space-y-1 mt-2">
                    {audioDuration > 0 && (
                      <p className="text-sm text-slate-600">
                        Длительность: {Math.floor(audioDuration / 60)}:{String(Math.floor(audioDuration % 60)).padStart(2, '0')}
                      </p>
                    )}
                    {generationTime > 0 && (
                      <div className="flex gap-4 text-xs text-slate-500">
                        <span>⏱️ Время генерации: {generationTime.toFixed(1)}с</span>
                        {audioSpeed > 0 && (
                          <span className="text-green-600 font-semibold">
                            ⚡ Скорость: {audioSpeed.toFixed(1)}x реального времени
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
                    Your browser does not support the audio element.
                  </audio>
                  <a href={audioUrl} download>
                    <Button className="w-full" variant="outline" data-testid="download-button">
                      <Download className="w-4 h-4 mr-2" />
                      Download Audio
                    </Button>
                  </a>
                </CardContent>
              </Card>
            )}
            
            {/* History */}
            {history.length > 0 && (
              <Card className="backdrop-blur-sm bg-white/80 border-slate-200 shadow-xl" data-testid="history-card">
                <CardHeader>
                  <CardTitle>Recent Generations</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {history.slice(0, 5).map((item) => (
                      <div key={item.id} className="p-3 bg-slate-50 rounded-lg border border-slate-200" data-testid={'history-item-' + item.id}>
                        <p className="text-sm text-slate-700 mb-2">{item.text}</p>
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-slate-500">{new Date(item.created_at).toLocaleString()}</span>
                          <a href={API + item.audio_url} download>
                            <Button size="sm" variant="ghost" data-testid={'history-download-' + item.id}>
                              <Download className="w-3 h-3" />
                            </Button>
                          </a>
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