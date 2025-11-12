import React, { useEffect, useState } from 'react';
import { Progress } from '@/components/ui/progress';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { 
  Loader2, CheckCircle, Clock, Zap, 
  Activity, TrendingUp, Sparkles 
} from 'lucide-react';

/**
 * EnhancedProgress Component - Beautiful progress visualization
 * Inspired by Revid AI's progress tracking with ETA and stages
 */
const EnhancedProgress = ({
  progress = 0,
  stage = '',
  message = '',
  eta = '',
  speed = 0,
  completedSegments = 0,
  totalSegments = 0,
  queuePosition = 0,
  isActive = false,
  isComplete = false,
  type = 'default', // 'text', 'audio', 'video', 'default'
  className = ''
}) => {
  const [smoothProgress, setSmoothProgress] = useState(progress);

  // Smooth progress animation
  useEffect(() => {
    const timer = setTimeout(() => {
      setSmoothProgress(progress);
    }, 100);
    return () => clearTimeout(timer);
  }, [progress]);

  // Type-specific styling
  const typeConfig = {
    text: {
      color: 'purple',
      icon: Sparkles,
      gradient: 'from-purple-500 to-pink-500'
    },
    audio: {
      color: 'blue',
      icon: Activity,
      gradient: 'from-blue-500 to-cyan-500'
    },
    video: {
      color: 'green',
      icon: TrendingUp,
      gradient: 'from-green-500 to-emerald-500'
    },
    default: {
      color: 'gray',
      icon: Loader2,
      gradient: 'from-gray-500 to-slate-500'
    }
  };

  const config = typeConfig[type] || typeConfig.default;
  const Icon = config.icon;

  // Format speed for display
  const formatSpeed = (speed) => {
    if (!speed || speed === 0) return null;
    if (speed < 1) return `${(speed * 1000).toFixed(0)}ms/seg`;
    return `${speed.toFixed(1)}x`;
  };

  if (!isActive && !isComplete) return null;

  return (
    <Card className={`${className} border-2 ${isComplete ? 'border-green-500 bg-green-50 dark:bg-green-950/20' : `border-${config.color}-200 dark:border-${config.color}-800`}`}>
      <CardContent className="p-6 space-y-4">
        {/* Header with Stage and Status */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`
              w-10 h-10 rounded-full flex items-center justify-center
              ${isComplete 
                ? 'bg-green-100 dark:bg-green-900' 
                : `bg-${config.color}-100 dark:bg-${config.color}-900`
              }
            `}>
              {isComplete ? (
                <CheckCircle className="w-6 h-6 text-green-600 dark:text-green-400" />
              ) : (
                <Icon className={`w-6 h-6 text-${config.color}-600 dark:text-${config.color}-400 ${!isComplete && 'animate-spin'}`} />
              )}
            </div>
            <div>
              <h3 className={`font-semibold text-lg ${isComplete ? 'text-green-700 dark:text-green-300' : 'text-gray-900 dark:text-white'}`}>
                {stage || 'Processing'}
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {message}
              </p>
            </div>
          </div>

          {/* Progress Badge */}
          <Badge variant={isComplete ? 'default' : 'secondary'} className={`
            text-lg font-bold px-4 py-2
            ${isComplete 
              ? 'bg-green-600 text-white' 
              : `bg-${config.color}-600 text-white`
            }
          `}>
            {Math.round(smoothProgress)}%
          </Badge>
        </div>

        {/* Progress Bar */}
        <div className="space-y-2">
          <Progress 
            value={smoothProgress} 
            className={`h-3 ${isComplete ? '' : `bg-${config.color}-100 dark:bg-${config.color}-900/30`}`}
          />
          
          {/* Segments Progress */}
          {totalSegments > 0 && !isComplete && (
            <div className="flex items-center justify-between text-xs text-gray-600 dark:text-gray-400">
              <span>Segment {completedSegments} of {totalSegments}</span>
              <span>{totalSegments - completedSegments} remaining</span>
            </div>
          )}
        </div>

        {/* Stats Row */}
        {!isComplete && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {/* ETA */}
            {eta && (
              <div className="flex items-center gap-2 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <Clock className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">ETA</p>
                  <p className="text-sm font-semibold text-gray-900 dark:text-white">{eta}</p>
                </div>
              </div>
            )}

            {/* Speed */}
            {speed > 0 && formatSpeed(speed) && (
              <div className="flex items-center gap-2 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <Zap className="w-4 h-4 text-yellow-600 dark:text-yellow-400" />
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Speed</p>
                  <p className="text-sm font-semibold text-gray-900 dark:text-white">{formatSpeed(speed)}</p>
                </div>
              </div>
            )}

            {/* Queue Position */}
            {queuePosition > 0 && (
              <div className="flex items-center gap-2 p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg col-span-2">
                <Loader2 className="w-4 h-4 text-amber-600 dark:text-amber-400 animate-spin" />
                <div>
                  <p className="text-xs text-amber-700 dark:text-amber-400">In Queue</p>
                  <p className="text-sm font-semibold text-amber-900 dark:text-amber-300">
                    Position #{queuePosition}
                  </p>
                </div>
              </div>
            )}

            {/* Completion Status */}
            {totalSegments > 0 && queuePosition === 0 && (
              <div className="flex items-center gap-2 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <Activity className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Progress</p>
                  <p className="text-sm font-semibold text-gray-900 dark:text-white">
                    {completedSegments}/{totalSegments}
                  </p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Complete Message */}
        {isComplete && (
          <div className="flex items-center gap-2 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
            <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0" />
            <p className="text-sm font-medium text-green-700 dark:text-green-300">
              ✨ Generation complete! Your content is ready.
            </p>
          </div>
        )}

        {/* Loading Animation Bar */}
        {!isComplete && smoothProgress < 100 && (
          <div className="relative h-1 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div className={`
              absolute inset-y-0 left-0 w-1/3 bg-gradient-to-r ${config.gradient} 
              animate-pulse opacity-50
            `} 
            style={{
              animation: 'shimmer 2s infinite',
            }} />
          </div>
        )}
      </CardContent>

      <style jsx>{`
        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(400%); }
        }
      `}</style>
    </Card>
  );
};

export default EnhancedProgress;