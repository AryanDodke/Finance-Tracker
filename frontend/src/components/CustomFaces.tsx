import React from 'react';

interface FaceProps extends React.SVGProps<SVGSVGElement> {
  name: string;
}

export function CustomFace({ name, className = "", ...props }: FaceProps) {
  // Common styles for the hand-drawn "koboyo" look (irregular, slightly wobbly strokes)
  const handDrawnStyle = {
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 2.5,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
  };

  const getFacePaths = () => {
    switch (name) {
      case 'face-personal': // 👤 Basic happy face
        return (
          <>
            <path d="M50 10 C 25 12, 10 30, 12 55 C 14 80, 30 90, 50 90 C 75 88, 90 70, 88 45 C 86 20, 70 8, 50 10 Z" />
            <path d="M35 40 Q 40 35 45 40" />
            <path d="M55 40 Q 60 35 65 40" />
            <path d="M35 60 Q 50 75 65 60" />
          </>
        );
      case 'face-rent': // 🏠 House face (stressed about rent!)
        return (
          <>
            <path d="M10 50 L 50 15 L 90 50" />
            <path d="M20 50 L 20 90 L 80 90 L 80 50" />
            <circle cx="35" cy="65" r="3" fill="currentColor" />
            <circle cx="65" cy="65" r="3" fill="currentColor" />
            <path d="M45 80 Q 50 70 55 80" />
          </>
        );
      case 'face-food': // 🍔 Drooling / hungry face
        return (
          <>
            <path d="M50 10 C 25 12, 10 30, 12 55 C 14 80, 30 90, 50 90 C 75 88, 90 70, 88 45 C 86 20, 70 8, 50 10 Z" />
            <circle cx="35" cy="40" r="4" fill="currentColor" />
            <circle cx="65" cy="40" r="4" fill="currentColor" />
            <path d="M40 60 Q 50 80 60 60" />
            <path d="M55 70 Q 55 85 50 85 Q 45 85 45 70" fill="currentColor" />
          </>
        );
      case 'face-travel': // ✈️ Travel face (excited, star eyes)
        return (
          <>
            <path d="M50 10 C 25 12, 10 30, 12 55 C 14 80, 30 90, 50 90 C 75 88, 90 70, 88 45 C 86 20, 70 8, 50 10 Z" />
            <path d="M30 35 L 40 35 L 35 45 Z" fill="currentColor" />
            <path d="M60 35 L 70 35 L 65 45 Z" fill="currentColor" />
            <path d="M30 60 Q 50 80 70 60 Z" fill="currentColor" />
          </>
        );
      case 'face-home': // 🛒 Focused face
        return (
          <>
            <path d="M50 10 C 25 12, 10 30, 12 55 C 14 80, 30 90, 50 90 C 75 88, 90 70, 88 45 C 86 20, 70 8, 50 10 Z" />
            <path d="M30 38 L 45 38" />
            <path d="M55 38 L 70 38" />
            <path d="M40 65 L 60 65" />
          </>
        );
      case 'face-outing': // 🍻 Cool face with sunglasses
        return (
          <>
            <path d="M50 10 C 25 12, 10 30, 12 55 C 14 80, 30 90, 50 90 C 75 88, 90 70, 88 45 C 86 20, 70 8, 50 10 Z" />
            <path d="M25 40 Q 35 45 45 40 Z" fill="currentColor" />
            <path d="M55 40 Q 65 45 75 40 Z" fill="currentColor" />
            <path d="M45 40 L 55 40" />
            <path d="M35 65 Q 50 75 60 60" />
          </>
        );
      case 'face-transfer': // 🔄 Transfer face (looking sideways)
        return (
          <>
            <path d="M50 10 C 25 12, 10 30, 12 55 C 14 80, 30 90, 50 90 C 75 88, 90 70, 88 45 C 86 20, 70 8, 50 10 Z" />
            <circle cx="25" cy="40" r="3" fill="currentColor" />
            <circle cx="55" cy="40" r="3" fill="currentColor" />
            <path d="M40 65 Q 50 68 60 65" />
          </>
        );
      case 'face-income': // 💰 Money face
        return (
          <>
            <path d="M50 10 C 25 12, 10 30, 12 55 C 14 80, 30 90, 50 90 C 75 88, 90 70, 88 45 C 86 20, 70 8, 50 10 Z" />
            <path d="M30 35 Q 35 30 40 35 Q 40 45 35 45 Q 30 45 35 40" />
            <path d="M35 30 L 35 48" />
            <path d="M60 35 Q 65 30 70 35 Q 70 45 65 45 Q 60 45 65 40" />
            <path d="M65 30 L 65 48" />
            <path d="M30 65 C 40 80, 60 80, 70 65" />
          </>
        );
      case 'face-unknown': // ❓ Confused face
      default:
        return (
          <>
            <path d="M50 10 C 25 12, 10 30, 12 55 C 14 80, 30 90, 50 90 C 75 88, 90 70, 88 45 C 86 20, 70 8, 50 10 Z" />
            <path d="M30 35 Q 35 30 40 35" />
            <path d="M60 40 Q 65 35 70 40" />
            <path d="M30 70 Q 40 55 50 65 T 70 60" />
          </>
        );
    }
  };

  return (
    <svg 
      aria-hidden="true"
      viewBox="0 0 100 100" 
      className={`inline-block w-5 h-5 mr-2 align-text-bottom ${className}`} 
      {...props}
      {...handDrawnStyle}
    >
      {getFacePaths()}
    </svg>
  );
}
