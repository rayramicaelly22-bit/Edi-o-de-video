import React from "react";

type P = {size?: number; color?: string};

export const ArrowUp: React.FC<P> = ({size = 64, color = "#fff"}) => (
  <svg width={size} height={size} viewBox="0 0 24 24">
    <path d="M12 2.5 L20 10.5 H14.6 V21.5 H9.4 V10.5 H4 Z" fill={color} />
  </svg>
);

export const TurnLeft: React.FC<P> = ({size = 64, color = "#fff"}) => (
  <svg width={size} height={size} viewBox="0 0 24 24">
    <path d="M18.5 21.5 V13 C18.5 10.2 16.3 8 13.5 8 H9.5 V3.5 L2.5 10 L9.5 16.5 V12 H13.5 C14.1 12 14.5 12.4 14.5 13 V21.5 Z" fill={color} />
  </svg>
);

export const Roundabout: React.FC<P> = ({size = 64, color = "#fff"}) => (
  <svg width={size} height={size} viewBox="0 0 24 24">
    <circle cx="12" cy="11" r="5.2" fill="none" stroke={color} strokeWidth="2.6" />
    <path d="M12 2 L16.5 6.8 H13.3 V9 H10.7 V6.8 H7.5 Z" fill={color} />
    <rect x="10.7" y="16" width="2.6" height="6" fill={color} />
  </svg>
);

export const Pin: React.FC<P & {hole?: string}> = ({size = 64, color = "#ff2d55", hole = "#fff"}) => (
  <svg width={size} height={size} viewBox="0 0 24 24">
    <path d="M12 1.5 C7.8 1.5 4.5 4.8 4.5 9 C4.5 14.6 12 22.5 12 22.5 C12 22.5 19.5 14.6 19.5 9 C19.5 4.8 16.2 1.5 12 1.5 Z" fill={color} />
    <circle cx="12" cy="9" r="3" fill={hole} />
  </svg>
);

export const Hospital: React.FC<P> = ({size = 64, color = "#ff3b47"}) => (
  <svg width={size} height={size} viewBox="0 0 24 24">
    <rect x="2" y="2" width="20" height="20" rx="5" fill={color} />
    <path d="M10 6 H14 V10 H18 V14 H14 V18 H10 V14 H6 V10 H10 Z" fill="#fff" />
  </svg>
);

export const Bike: React.FC<P> = ({size = 64, color = "#fff"}) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="5.5" cy="16.5" r="3.6" />
    <circle cx="18.5" cy="16.5" r="3.6" />
    <path d="M5.5 16.5 L9.5 9 H15.5 L18.5 16.5 M9.5 9 L12.2 16.5 H5.5 M15.5 9 L14.6 6.5 H12.6 M8.2 6.8 H11" />
  </svg>
);

export const Ball: React.FC<P> = ({size = 64, color = "#fff"}) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="9.6" strokeWidth="2.2" />
    <path d="M12 8.4 L15.4 10.9 L14.1 14.9 H9.9 L8.6 10.9 Z" fill={color} />
    <path d="M12 8.4 V2.6 M15.4 10.9 L21 9.1 M14.1 14.9 L17.6 19.6 M9.9 14.9 L6.4 19.6 M8.6 10.9 L3 9.1" />
  </svg>
);

export const Paw: React.FC<P> = ({size = 64, color = "#fff"}) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill={color}>
    <ellipse cx="12" cy="16.3" rx="5.2" ry="4.4" />
    <ellipse cx="5.2" cy="10.6" rx="2.1" ry="2.7" />
    <ellipse cx="9.1" cy="6.4" rx="2.1" ry="2.8" />
    <ellipse cx="14.9" cy="6.4" rx="2.1" ry="2.8" />
    <ellipse cx="18.8" cy="10.6" rx="2.1" ry="2.7" />
  </svg>
);

export const Heart: React.FC<P> = ({size = 64, color = "#ff2d55"}) => (
  <svg width={size} height={size} viewBox="0 0 24 24">
    <path d="M12 21 L10.6 19.7 C5.4 15 2 11.9 2 8.1 C2 5 4.4 2.6 7.5 2.6 C9.2 2.6 10.9 3.4 12 4.7 C13.1 3.4 14.8 2.6 16.5 2.6 C19.6 2.6 22 5 22 8.1 C22 11.9 18.6 15 13.4 19.7 Z" fill={color} />
  </svg>
);

export const Bookmark: React.FC<P> = ({size = 64, color = "#fff"}) => (
  <svg width={size} height={size} viewBox="0 0 24 24">
    <path d="M6 2.5 H18 C18.8 2.5 19.5 3.2 19.5 4 V21.5 L12 16.8 L4.5 21.5 V4 C4.5 3.2 5.2 2.5 6 2.5 Z" fill={color} />
  </svg>
);
