package ca.optiframe.api;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;

@SpringBootApplication
@ConfigurationPropertiesScan
public class OptiframeApiApplication {

	public static void main(String[] args) {
		SpringApplication.run(OptiframeApiApplication.class, args);
	}

}
