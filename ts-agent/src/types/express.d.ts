declare global {
  namespace Express {
    interface Response {
      flush?: () => void;
    }
  }
}

export {};
