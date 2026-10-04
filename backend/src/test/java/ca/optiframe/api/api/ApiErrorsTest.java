package ca.optiframe.api.api;

import static org.hamcrest.Matchers.containsString;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.options;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.web.servlet.MockMvc;

/** Client mistakes get a 4xx with a French message naming the problem, never a 500 (issue #18). */
@SpringBootTest
@AutoConfigureMockMvc
class ApiErrorsTest {

	private static final MockMultipartFile IMAGE = new MockMultipartFile("image", "photo.jpg", "image/jpeg",
			new byte[] { (byte) 0xff, (byte) 0xd8, (byte) 0xff });

	@Autowired
	MockMvc mvc;

	@Test
	void invalidEyeIs400NamingTheParameterAndItsValues() throws Exception {
		mvc.perform(multipart("/api/measure").file(IMAGE).param("eye", "RIGHT"))
				.andExpect(status().isBadRequest())
				.andExpect(jsonPath("$.code").value("BAD_REQUEST"))
				.andExpect(jsonPath("$.message").value(containsString("« eye »")))
				.andExpect(jsonPath("$.message").value(containsString("« RIGHT »")))
				.andExpect(jsonPath("$.message").value(containsString("L, R")));
	}

	@Test
	void missingEyeIs400() throws Exception {
		mvc.perform(multipart("/api/measure").file(IMAGE))
				.andExpect(status().isBadRequest())
				.andExpect(jsonPath("$.message").value("Paramètre « eye » manquant."));
	}

	@Test
	void missingImageIs400() throws Exception {
		mvc.perform(multipart("/api/measure").param("eye", "R"))
				.andExpect(status().isBadRequest())
				.andExpect(jsonPath("$.message").value("Fichier « image » manquant."));
	}

	@Test
	void getOnMeasureIs405WithAllowHeader() throws Exception {
		mvc.perform(get("/api/measure"))
				.andExpect(status().isMethodNotAllowed())
				.andExpect(header().string("Allow", containsString("POST")))
				.andExpect(jsonPath("$.code").value("METHOD_NOT_ALLOWED"))
				.andExpect(jsonPath("$.message").value(containsString("POST")));
	}

	@Test
	void jsonBodyIs415() throws Exception {
		mvc.perform(post("/api/measure").contentType(MediaType.APPLICATION_JSON).content("{}"))
				.andExpect(status().isUnsupportedMediaType())
				.andExpect(jsonPath("$.code").value("UNSUPPORTED_MEDIA_TYPE"))
				.andExpect(jsonPath("$.message").value(containsString("multipart/form-data")));
	}

	@Test
	void theDeployedAppMayCallTheApi() throws Exception {
		// The worker forwards https://optiframe.app to the Cloud Run host: a cross-origin request for Spring.
		mvc.perform(options("/api/measure").header("Origin", "https://optiframe.app")
				.header("Access-Control-Request-Method", "POST"))
				.andExpect(status().isOk())
				.andExpect(header().string("Access-Control-Allow-Origin", "https://optiframe.app"));
	}

	@Test
	void otherSitesMayNot() throws Exception {
		mvc.perform(options("/api/measure").header("Origin", "https://example.com")
				.header("Access-Control-Request-Method", "POST"))
				.andExpect(status().isForbidden());
	}

	@Test
	void unknownApiPathIs404() throws Exception {
		mvc.perform(get("/api/nothing-here"))
				.andExpect(status().isNotFound())
				.andExpect(jsonPath("$.code").value("NOT_FOUND"));
	}

}
