import React from 'react';

const LoadingSpinner = ({ size = 'md', text = 'Loading...' }) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
  };

  return (
    <div className="flex flex-col items-center justify-center p-8">
      <div className={`${sizeClasses[size]} animate-spin`}>
        <div className="h-full w-full rounded-full border-4 border-gray-200 border-t-primary-600"></div>
      </div>
      {text && (
        <p className="mt-3 text-sm text-gray-600">{text}</p>
      )}
    </div>
  );
};

export default LoadingSpinner; 