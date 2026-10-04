package ca.optiframe.api.api;

import java.util.Arrays;
import java.util.stream.Collectors;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.ResponseEntity;
import org.springframework.web.ErrorResponse;
import org.springframework.web.HttpMediaTypeNotSupportedException;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.multipart.MaxUploadSizeExceededException;
import org.springframework.web.multipart.MultipartException;
import org.springframework.web.multipart.support.MissingServletRequestPartException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

import ca.optiframe.api.api.dto.ApiError;
import ca.optiframe.api.vision.MeasurementException;

/**
 * Every error reaches the user as a readable French message, never a stack trace. Client errors (4xx) are logged
 * as one WARN line; only real server errors are logged as ERROR with their stack.
 */
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

	@ExceptionHandler(MethodArgumentTypeMismatchException.class)
	ResponseEntity<ApiError> typeMismatch(MethodArgumentTypeMismatchException e) {
		String message = "Paramètre « " + e.getName() + " » invalide : « " + e.getValue() + " ».";
		Class<?> type = e.getRequiredType();
		if (type != null && type.isEnum()) {
			message += " Valeurs acceptées : " + Arrays.stream(type.getEnumConstants())
					.map(Object::toString)
					.collect(Collectors.joining(", ")) + ".";
		}
		return clientError(HttpStatus.BAD_REQUEST, "BAD_REQUEST", message, null, e);
	}

	@ExceptionHandler(MissingServletRequestParameterException.class)
	ResponseEntity<ApiError> missingParameter(MissingServletRequestParameterException e) {
		return clientError(HttpStatus.BAD_REQUEST, "BAD_REQUEST",
				"Paramètre « " + e.getParameterName() + " » manquant.", null, e);
	}

	@ExceptionHandler(MissingServletRequestPartException.class)
	ResponseEntity<ApiError> missingPart(MissingServletRequestPartException e) {
		return clientError(HttpStatus.BAD_REQUEST, "BAD_REQUEST",
				"Fichier « " + e.getRequestPartName() + " » manquant.", null, e);
	}

	@ExceptionHandler(MultipartException.class)
	ResponseEntity<ApiError> badMultipart(MultipartException e) {
		return clientError(HttpStatus.BAD_REQUEST, "BAD_REQUEST",
				"Formulaire invalide : envoyez la photo en multipart/form-data.", null, e);
	}

	@ExceptionHandler(HttpRequestMethodNotSupportedException.class)
	ResponseEntity<ApiError> methodNotAllowed(HttpRequestMethodNotSupportedException e) {
		String allowed = e.getSupportedHttpMethods() == null ? ""
				: " Utilisez " + e.getSupportedHttpMethods().stream()
						.map(Object::toString)
						.collect(Collectors.joining(" ou ")) + ".";
		return clientError(HttpStatus.METHOD_NOT_ALLOWED, "METHOD_NOT_ALLOWED",
				"Méthode " + e.getMethod() + " non permise." + allowed, e.getHeaders(), e);
	}

	@ExceptionHandler(HttpMediaTypeNotSupportedException.class)
	ResponseEntity<ApiError> unsupportedMediaType(HttpMediaTypeNotSupportedException e) {
		return clientError(HttpStatus.UNSUPPORTED_MEDIA_TYPE, "UNSUPPORTED_MEDIA_TYPE",
				"Format de requête non pris en charge (" + e.getContentType()
						+ "). Envoyez la photo en multipart/form-data.",
				e.getHeaders(), e);
	}

	@ExceptionHandler(NoResourceFoundException.class)
	ResponseEntity<ApiError> notFound(NoResourceFoundException e) {
		return clientError(HttpStatus.NOT_FOUND, "NOT_FOUND", "Adresse introuvable.", e.getHeaders(), e);
	}

	@ExceptionHandler(Exception.class)
	ResponseEntity<ApiError> unexpected(Exception e) {
		// Any other error Spring already maps to a 4xx (406, 400 on a bad body...) keeps its status.
		if (e instanceof ErrorResponse er && er.getStatusCode().is4xxClientError()) {
			HttpStatusCode status = er.getStatusCode();
			return clientError(status, HttpStatus.valueOf(status.value()).name(), "Requête invalide.",
					er.getHeaders(), e);
		}
		log.error("Unexpected error", e);
		return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
				.body(new ApiError("INTERNAL", "Erreur inattendue du serveur. Réessayez dans un instant."));
	}

	private static ResponseEntity<ApiError> clientError(HttpStatusCode status, String code, String message,
			HttpHeaders headers, Exception e) {
		log.warn("{} {}: {}", status.value(), code, e.getMessage());
		ResponseEntity.BodyBuilder response = ResponseEntity.status(status);
		if (headers != null) {
			response.headers(headers);
		}
		return response.body(new ApiError(code, message));
	}

}
