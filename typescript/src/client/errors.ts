import { ErrorModel, ErrorCode } from "../models/errors.js";

export class BaseError extends Error {
  constructor(message: string, options?: ErrorOptions) {
    super(message, options);

    Object.setPrototypeOf(this, new.target.prototype);

    if ((Error as any).captureStackTrace) {
      (Error as any).captureStackTrace(this, this.constructor);
    }
  }
}

export class FetchError extends BaseError {
  constructor(
    message: string,
    public response?: Response,
    options?: ErrorOptions
  ) {
    super(message, options);
    this.name = "FetchError";
  }
}

export class HTTPError extends BaseError {
  statusCode: number;
  headers: Headers;
  body?: unknown;

  constructor(response: Response, body?: unknown) {
    super(`HTTPError: status ${response.status}`);
    this.name = "HTTPError";
    this.statusCode = response.status;
    this.headers = response.headers;
    this.body = body;
  }
}

export class ACPError extends BaseError {
  error: ErrorModel;
  code: ErrorCode;

  constructor(error: ErrorModel) {
    super(error.message);
    this.name = "ACPError";
    this.error = error;
    this.code = error.code;
  }
}
