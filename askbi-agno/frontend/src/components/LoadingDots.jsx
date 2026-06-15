import React from 'react';

const LoadingDots = () => (
    <div className="flex gap-1.5 items-center px-5 py-4 rounded-3xl bg-white border border-gray-100 shadow-sm text-gray-400 rounded-tl-none">
        <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"></span>
        <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{animationDelay: "0.15s"}}></span>
        <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{animationDelay: "0.3s"}}></span>
    </div>
);

export default LoadingDots;


