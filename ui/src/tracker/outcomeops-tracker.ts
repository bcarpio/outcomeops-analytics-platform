/**
 * OutcomeOps Analytics Tracker
 *
 * Lightweight first-party analytics tracking library.
 * Tracks pageviews, sessions, scroll depth, time on page, and SPA navigation.
 *
 * Usage:
 *   <script src="https://t.yourdomain.com/tracker.js" data-domain="yourdomain.com"></script>
 *
 * Or programmatically:
 *   OutcomeOpsTracker.init({ domain: 'yourdomain.com', endpoint: 'https://t.yourdomain.com' });
 */

interface TrackerConfig {
  domain: string;
  endpoint?: string;
  trackScrollDepth?: boolean;
  trackTimeOnPage?: boolean;
  sessionTimeout?: number; // minutes
}

interface TrackingEvent {
  session_id: string;
  event_type: string;
  domain: string;
  path: string;
  timestamp: string;
  event_id?: string;
  referrer?: string;
  previous_path?: string;
  scroll_depth?: number;
  time_on_page?: number;
  user_agent?: string;
  screen_width?: number;
  screen_height?: number;
  viewport_width?: number;
  viewport_height?: number;
}

const SESSION_KEY = 'oo_sid';
const SESSION_EXPIRY_KEY = 'oo_exp';
const DEFAULT_SESSION_TIMEOUT = 30; // minutes

class OutcomeOpsTrackerClass {
  private config: TrackerConfig | null = null;
  private sessionId: string | null = null;
  private pageLoadTime: number = 0;
  private maxScrollDepth: number = 0;
  private scrollMilestones: Set<number> = new Set();
  private eventQueue: TrackingEvent[] = [];
  private flushTimer: number | null = null;
  private previousPath: string = '';
  private isInitialized: boolean = false;

  /**
   * Initialize the tracker with configuration
   */
  init(config: TrackerConfig): void {
    if (this.isInitialized) return;

    this.config = {
      trackScrollDepth: true,
      trackTimeOnPage: true,
      sessionTimeout: DEFAULT_SESSION_TIMEOUT,
      ...config,
    };

    // Derive endpoint from domain if not provided
    if (!this.config.endpoint) {
      this.config.endpoint = `https://t.${this.config.domain}`;
    }

    this.sessionId = this.getOrCreateSession();
    this.pageLoadTime = Date.now();
    this.previousPath = '';

    // Track initial pageview
    this.trackPageview();

    // Set up event listeners
    this.setupListeners();
    this.isInitialized = true;
  }

  /**
   * Get existing session or create new one
   */
  private getOrCreateSession(): string {
    const storedId = localStorage.getItem(SESSION_KEY);
    const storedExpiry = localStorage.getItem(SESSION_EXPIRY_KEY);
    const now = Date.now();

    if (storedId && storedExpiry && parseInt(storedExpiry) > now) {
      // Extend session
      this.extendSession();
      return storedId;
    }

    // Create new session
    const newId = this.generateId();
    localStorage.setItem(SESSION_KEY, newId);
    this.extendSession();
    this.trackEvent('session_start', {});
    return newId;
  }

  /**
   * Extend session expiry
   */
  private extendSession(): void {
    const timeout = (this.config?.sessionTimeout || DEFAULT_SESSION_TIMEOUT) * 60 * 1000;
    localStorage.setItem(SESSION_EXPIRY_KEY, (Date.now() + timeout).toString());
  }

  /**
   * Generate a random ID
   */
  private generateId(): string {
    return Math.random().toString(36).substring(2, 10) +
           Math.random().toString(36).substring(2, 10);
  }

  /**
   * Track a pageview
   */
  trackPageview(): void {
    const path = window.location.pathname;

    this.trackEvent('pageview', {
      referrer: document.referrer || undefined,
      previous_path: this.previousPath || undefined,
      user_agent: navigator.userAgent,
      screen_width: window.screen.width,
      screen_height: window.screen.height,
      viewport_width: window.innerWidth,
      viewport_height: window.innerHeight,
    });

    // Reset page-specific tracking
    this.pageLoadTime = Date.now();
    this.maxScrollDepth = 0;
    this.scrollMilestones.clear();
    this.previousPath = path;
  }

  /**
   * Track SPA navigation
   */
  trackNavigation(): void {
    const path = window.location.pathname;
    if (path === this.previousPath) return;

    // Send time on page for previous page before tracking new page
    if (this.config?.trackTimeOnPage && this.previousPath) {
      this.sendTimeOnPage();
    }

    this.trackEvent('navigation', {
      previous_path: this.previousPath,
    });

    // Reset for new page
    this.pageLoadTime = Date.now();
    this.maxScrollDepth = 0;
    this.scrollMilestones.clear();
    this.previousPath = path;
  }

  /**
   * Track scroll depth milestone
   */
  private trackScrollMilestone(depth: number): void {
    if (this.scrollMilestones.has(depth)) return;
    this.scrollMilestones.add(depth);

    this.trackEvent('scroll', {
      scroll_depth: depth,
    });
  }

  /**
   * Send time on page event
   */
  private sendTimeOnPage(): void {
    const timeOnPage = Math.round((Date.now() - this.pageLoadTime) / 1000);
    if (timeOnPage < 1) return;

    this.trackEvent('time_on_page', {
      time_on_page: timeOnPage,
      scroll_depth: this.maxScrollDepth,
    });
  }

  /**
   * Track a custom event
   */
  trackEvent(eventType: string, data: Partial<TrackingEvent>): void {
    if (!this.config || !this.sessionId) return;

    const event: TrackingEvent = {
      session_id: this.sessionId,
      event_type: eventType,
      domain: this.config.domain,
      path: window.location.pathname,
      timestamp: new Date().toISOString(),
      event_id: this.generateId().substring(0, 8),
      ...data,
    };

    this.eventQueue.push(event);
    this.extendSession();
    this.scheduleFlush();
  }

  /**
   * Schedule a flush of the event queue
   */
  private scheduleFlush(): void {
    if (this.flushTimer) return;

    this.flushTimer = window.setTimeout(() => {
      this.flush();
      this.flushTimer = null;
    }, 1000);
  }

  /**
   * Flush event queue to server
   */
  flush(): void {
    if (!this.config || this.eventQueue.length === 0) return;

    const events = [...this.eventQueue];
    this.eventQueue = [];

    const endpoint = `${this.config.endpoint}/t/batch`;
    const payload = JSON.stringify({ events });

    // Use sendBeacon for reliability (works even when page is closing)
    if (navigator.sendBeacon) {
      navigator.sendBeacon(endpoint, payload);
    } else {
      // Fallback to fetch
      fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: payload,
        keepalive: true,
      }).catch(() => {
        // Silently fail - analytics should never break the site
      });
    }
  }

  /**
   * Set up event listeners
   */
  private setupListeners(): void {
    // Scroll tracking
    if (this.config?.trackScrollDepth) {
      let ticking = false;
      window.addEventListener('scroll', () => {
        if (!ticking) {
          window.requestAnimationFrame(() => {
            this.handleScroll();
            ticking = false;
          });
          ticking = true;
        }
      }, { passive: true });
    }

    // SPA navigation (History API)
    const originalPushState = history.pushState;
    const originalReplaceState = history.replaceState;

    history.pushState = (...args) => {
      originalPushState.apply(history, args);
      this.trackNavigation();
    };

    history.replaceState = (...args) => {
      originalReplaceState.apply(history, args);
      this.trackNavigation();
    };

    window.addEventListener('popstate', () => {
      this.trackNavigation();
    });

    // Page visibility / unload
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'hidden') {
        if (this.config?.trackTimeOnPage) {
          this.sendTimeOnPage();
        }
        this.trackEvent('session_end', {});
        this.flush();
      }
    });

    // Flush on page unload (backup)
    window.addEventListener('pagehide', () => {
      this.flush();
    });
  }

  /**
   * Handle scroll event
   */
  private handleScroll(): void {
    const scrollTop = window.scrollY || document.documentElement.scrollTop;
    const scrollHeight = document.documentElement.scrollHeight - window.innerHeight;

    if (scrollHeight <= 0) return;

    const scrollPercent = Math.round((scrollTop / scrollHeight) * 100);
    this.maxScrollDepth = Math.max(this.maxScrollDepth, scrollPercent);

    // Track milestones at 25%, 50%, 75%, 100%
    const milestones = [25, 50, 75, 100];
    for (const milestone of milestones) {
      if (scrollPercent >= milestone) {
        this.trackScrollMilestone(milestone);
      }
    }
  }
}

// Create singleton instance
const OutcomeOpsTracker = new OutcomeOpsTrackerClass();

// Auto-initialize from script tag data attributes
if (typeof document !== 'undefined') {
  const script = document.currentScript as HTMLScriptElement;
  if (script?.dataset.domain) {
    OutcomeOpsTracker.init({
      domain: script.dataset.domain,
      endpoint: script.dataset.endpoint,
      trackScrollDepth: script.dataset.scroll !== 'false',
      trackTimeOnPage: script.dataset.time !== 'false',
    });
  }
}

// Export for module usage
export { OutcomeOpsTracker, OutcomeOpsTrackerClass };
export type { TrackerConfig, TrackingEvent };
