import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import LandingSequence from '../components/landing/LandingSequence';

vi.mock('../components/landing/CinematicIntro', () => ({
  default: () => <div data-testid="cinematic-intro" />,
}));

describe('LandingSequence Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders skip intro button and calls onComplete when clicked', () => {
    const onComplete = vi.fn();
    render(<LandingSequence onComplete={onComplete} />);

    const skipBtn = screen.getByRole('button', { name: /Skip Introduction/i });
    expect(skipBtn).toBeInTheDocument();

    fireEvent.click(skipBtn);
    expect(onComplete).toHaveBeenCalled();
  });

  it('calls onComplete when any key is pressed', () => {
    const onComplete = vi.fn();
    render(<LandingSequence onComplete={onComplete} />);

    fireEvent.keyDown(window, { key: 'Escape' });
    expect(onComplete).toHaveBeenCalled();
  });

  it('automatically skips if prefers-reduced-motion is true', () => {
    const onComplete = vi.fn();
    const originalMatchMedia = window.matchMedia;

    window.matchMedia = vi.fn().mockImplementation((query) => ({
      matches: query === '(prefers-reduced-motion: reduce)',
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));

    render(<LandingSequence onComplete={onComplete} />);
    expect(onComplete).toHaveBeenCalled();

    window.matchMedia = originalMatchMedia;
  });
});
