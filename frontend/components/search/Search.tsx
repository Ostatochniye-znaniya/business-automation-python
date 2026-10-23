"use client";

import React from "react";

interface SearchProps {
  hint: string;
  value: string;
  onChange: (value: string) => void;
  size?: "small" | "large";
}

const Search: React.FC<SearchProps> = ({
  hint,
  value,
  onChange,
  size = "large",
}) => {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange(e.target.value);
  };

  const containerClassName = `search-container search-${size}`;
  const inputClassName = `search-input`;

  return (
    <div className={containerClassName}>
      <svg
        width="12"
        height="13"
        viewBox="0 0 12 13"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          d="M6 0.5C9.03757 0.5 11.5 2.96243 11.5 6C11.5 9.03757 9.03757 11.5 6 11.5C2.96243 11.5 0.5 9.03757 0.5 6C0.5 2.96243 2.96243 0.5 6 0.5Z"
          stroke="#A3A3A3"
        />
        <rect
          x="11.4072"
          y="12.3718"
          width="2.74729"
          height="0.500292"
          rx="0.250146"
          transform="rotate(-135 11.4072 12.3718)"
          fill="#D9D9D9"
          stroke="#A3A3A3"
          strokeWidth="0.500292"
        />
      </svg>
      <input
        className={inputClassName}
        type="text"
        placeholder={hint}
        value={value}
        onChange={handleChange}
      />
    </div>
  );
};

export default Search;
