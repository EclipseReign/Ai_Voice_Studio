import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, File, X, CheckCircle, AlertCircle } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';

/**
 * DragDropUpload Component - Modern drag & drop file upload
 * Inspired by Revid AI's upload interface
 */
const DragDropUpload = ({
  onFileSelect,
  acceptedFileTypes = {
    'video/*': ['.mp4', '.mov', '.avi', '.mkv']
  },
  maxSize = 500 * 1024 * 1024, // 500MB default
  uploadProgress = 0,
  isUploading = false,
  uploadComplete = false,
  uploadError = null,
  label = "Upload Video",
  description = "Drag and drop or click to browse",
  className = ""
}) => {
  const [selectedFile, setSelectedFile] = useState(null);

  const onDrop = useCallback((acceptedFiles, rejectedFiles) => {
    if (rejectedFiles.length > 0) {
      const rejection = rejectedFiles[0];
      let errorMessage = "File rejected";
      
      if (rejection.errors[0]?.code === 'file-too-large') {
        errorMessage = `File is too large. Maximum size is ${Math.round(maxSize / 1024 / 1024)}MB`;
      } else if (rejection.errors[0]?.code === 'file-invalid-type') {
        errorMessage = "Invalid file type";
      }
      
      if (onFileSelect) {
        onFileSelect(null, errorMessage);
      }
      return;
    }

    if (acceptedFiles.length > 0) {
      const file = acceptedFiles[0];
      setSelectedFile(file);
      if (onFileSelect) {
        onFileSelect(file, null);
      }
    }
  }, [onFileSelect, maxSize]);

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: acceptedFileTypes,
    maxSize: maxSize,
    multiple: false,
    disabled: isUploading
  });

  const removeFile = (e) => {
    e.stopPropagation();
    setSelectedFile(null);
    if (onFileSelect) {
      onFileSelect(null, null);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div className={`space-y-3 ${className}`}>
      <Card
        {...getRootProps()}
        className={`
          relative overflow-hidden transition-all duration-200 cursor-pointer
          ${isDragActive && !isDragReject ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/20 ring-2 ring-blue-500' : ''}
          ${isDragReject ? 'border-red-500 bg-red-50 dark:bg-red-950/20 ring-2 ring-red-500' : ''}
          ${isUploading ? 'opacity-60 cursor-not-allowed' : 'hover:border-blue-400 hover:bg-blue-50/50 dark:hover:bg-blue-950/10'}
          ${uploadComplete ? 'border-green-500 bg-green-50 dark:bg-green-950/20' : ''}
          ${uploadError ? 'border-red-500 bg-red-50 dark:bg-red-950/20' : ''}
        `}
      >
        <input {...getInputProps()} />
        
        <div className="p-8 text-center">
          {/* Upload Icon or Status */}
          {!selectedFile && !isUploading && !uploadComplete && (
            <div className="flex flex-col items-center space-y-4">
              <div className={`
                w-16 h-16 rounded-full flex items-center justify-center
                ${isDragActive ? 'bg-blue-100 dark:bg-blue-900' : 'bg-gray-100 dark:bg-gray-800'}
              `}>
                <Upload className={`w-8 h-8 ${isDragActive ? 'text-blue-600 dark:text-blue-400' : 'text-gray-400'}`} />
              </div>
              
              <div className="space-y-2">
                <p className="text-lg font-semibold text-gray-700 dark:text-gray-300">
                  {isDragActive ? 'Drop file here' : label}
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {description}
                </p>
                <p className="text-xs text-gray-400 dark:text-gray-500">
                  Max file size: {Math.round(maxSize / 1024 / 1024)}MB
                </p>
              </div>

              <Button variant="outline" size="sm" className="mt-2" type="button">
                Browse Files
              </Button>
            </div>
          )}

          {/* Selected File Info */}
          {selectedFile && !isUploading && !uploadComplete && (
            <div className="flex items-center justify-between p-4 bg-white dark:bg-gray-800 rounded-lg">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900 rounded-lg flex items-center justify-center">
                  <File className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                </div>
                <div className="text-left">
                  <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate max-w-[200px]">
                    {selectedFile.name}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {formatFileSize(selectedFile.size)}
                  </p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={removeFile}
                className="text-red-500 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950/20"
                type="button"
              >
                <X className="w-4 h-4" />
              </Button>
            </div>
          )}

          {/* Upload Progress */}
          {isUploading && (
            <div className="space-y-3">
              <div className="w-16 h-16 mx-auto bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center animate-pulse">
                <Upload className="w-8 h-8 text-blue-600 dark:text-blue-400" />
              </div>
              <p className="text-lg font-semibold text-gray-700 dark:text-gray-300">
                Uploading...
              </p>
              <Progress value={uploadProgress} className="w-full" />
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {uploadProgress}% complete
              </p>
            </div>
          )}

          {/* Upload Complete */}
          {uploadComplete && !uploadError && (
            <div className="flex flex-col items-center space-y-3">
              <div className="w-16 h-16 bg-green-100 dark:bg-green-900 rounded-full flex items-center justify-center">
                <CheckCircle className="w-8 h-8 text-green-600 dark:text-green-400" />
              </div>
              <p className="text-lg font-semibold text-green-700 dark:text-green-300">
                Upload Complete!
              </p>
              {selectedFile && (
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {selectedFile.name}
                </p>
              )}
            </div>
          )}

          {/* Upload Error */}
          {uploadError && (
            <div className="flex flex-col items-center space-y-3">
              <div className="w-16 h-16 bg-red-100 dark:bg-red-900 rounded-full flex items-center justify-center">
                <AlertCircle className="w-8 h-8 text-red-600 dark:text-red-400" />
              </div>
              <p className="text-lg font-semibold text-red-700 dark:text-red-300">
                Upload Failed
              </p>
              <p className="text-sm text-red-600 dark:text-red-400">
                {uploadError}
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={removeFile}
                className="mt-2"
                type="button"
              >
                Try Again
              </Button>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
};

export default DragDropUpload;