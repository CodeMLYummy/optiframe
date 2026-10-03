package ca.optiframe.api.sheet;

import java.io.IOException;
import java.io.InputStream;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.io.ClassPathResource;

import tools.jackson.databind.ObjectMapper;

@Configuration
public class SheetLayoutConfig {

	@Bean
	SheetLayout sheetLayout(ObjectMapper mapper) throws IOException {
		try (InputStream in = new ClassPathResource("sheet-layout.json").getInputStream()) {
			return mapper.readValue(in, SheetLayout.class);
		}
	}

}
