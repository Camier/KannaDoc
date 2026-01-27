/**
 * Logger utility for frontend
 * Provides consistent logging interface with environment-aware output
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LoggerInterface {
  debug: (...args: unknown[]) => void;
  info: (...args: unknown[]) => void;
  warn: (...args: unknown[]) => void;
  error: (...args: unknown[]) => void;
}

// Check if we're in development mode
const isDevelopment = process.env.NODE_ENV === 'development';

/**
 * Production-ready logger
 * - In development: logs to console with prefixes
 * - In production: only logs errors and warnings
 */
class Logger implements LoggerInterface {
  private formatMessage(level: LogLevel, args: unknown[]): string {
    const timestamp = new Date().toISOString();
    const message = args
      .map(arg => {
        if (arg instanceof Error) {
          return `${arg.message}\n${arg.stack}`;
        }
        return typeof arg === 'string' ? arg : JSON.stringify(arg);
      })
      .join(' ');
    return `[${timestamp}] [${level.toUpperCase()}] ${message}`;
  }

  debug(...args: unknown[]): void {
    if (isDevelopment) {
      console.debug(this.formatMessage('debug', args), ...args);
    }
  }

  info(...args: unknown[]): void {
    if (isDevelopment) {
      console.info(this.formatMessage('info', args), ...args);
    }
  }

  warn(...args: unknown[]): void {
    // Always show warnings
    console.warn(this.formatMessage('warn', args), ...args);
  }

  error(...args: unknown[]): void {
    // Always show errors
    console.error(this.formatMessage('error', args), ...args);
  }
}

// Export singleton instance
export const logger = new Logger();

// Also export a convenience function for module-level usage
export default logger;
