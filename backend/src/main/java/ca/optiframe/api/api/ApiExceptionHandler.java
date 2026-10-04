package ca.optiframe.api.api;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.multipart.MaxUploadSizeExceededException;
import org.springframework.web.multipart.MultipartException;
import org.springframework.web.multipart.support.MissingServletRequestPartException;

import ca.optiframe.api.api.dto.ApiError;
import ca.optiframe.api.vision.MeasurementException;

/** Every error reaches the user as a readable French message, never a stack trace. */
@RestControllerAdvice
public class ApiExceptionHandler {

	private static final Logger log = LoggerFactory.getLogger(ApiExceptionHandler.class);

	@ExceptionHandler(MeasurementException.class)
	@ResponseStatus(HttpStatus.UNPROCESSABLE_CONTENT)
	ApiError measurement(MeasurementException e) {
		return new ApiError(e.code().name(), e.getMessage());
	}

	@ExceptionHandler(MaxUploadSizeExceededException.class)
	@ResponseStatus(HttpStatus.CONTENT_TOO_LARGE)
	ApiError tooLarge() {
		return new ApiError("IMAGE_TOO_LARGE", "Photo trop lourde (20 Mo maximum).");
	}

	@ExceptionHandler({ MissingServletRequestParameterException.class, MissingServletRequestPartException.class,
			MethodArgumentTypeMismatchException.class, MultipartException.class })
	@ResponseStatus(HttpStatus.BAD_REQUEST)
	ApiError badRequest() {
		return new ApiError("BAD_REQUEST", "Requête invalide.");
	}

	@ExceptionHandler(Exception.class)
	@ResponseStatus(HttpStatus.INTERNAL_SERVER_ERROR)
	ApiError unexpected(Exception e) {
		log.error("Unexpected error", e);
		return new ApiError("INTERNAL", "Erreur inattendue du serveur. Réessayez dans un instant.");
	}

}
