package com.mulenet.api.platform;

import com.fasterxml.jackson.core.StreamReadConstraints;
import com.fasterxml.jackson.databind.cfg.CoercionAction;
import com.fasterxml.jackson.databind.cfg.CoercionInputShape;
import com.fasterxml.jackson.databind.type.LogicalType;
import org.springframework.boot.autoconfigure.jackson.Jackson2ObjectMapperBuilderCustomizer;
import org.springframework.context.annotation.*;

@Configuration
@Profile("platform")
public class StrictJson {
    @Bean public Jackson2ObjectMapperBuilderCustomizer strictScalarTypes() {
        return builder -> builder.postConfigurer(mapper -> {
            mapper.getFactory().setStreamReadConstraints(StreamReadConstraints.builder().maxNestingDepth(32).maxStringLength(4096).maxNumberLength(40).build());
            for (LogicalType type : new LogicalType[]{LogicalType.Integer, LogicalType.Float, LogicalType.Boolean}) {
                mapper.coercionConfigFor(type).setCoercion(CoercionInputShape.String, CoercionAction.Fail)
                    .setCoercion(CoercionInputShape.EmptyString, CoercionAction.Fail);
            }
            mapper.coercionConfigFor(LogicalType.Integer).setCoercion(CoercionInputShape.Float, CoercionAction.Fail)
                .setCoercion(CoercionInputShape.Boolean, CoercionAction.Fail);
            mapper.coercionConfigFor(LogicalType.Textual).setCoercion(CoercionInputShape.Integer, CoercionAction.Fail)
                .setCoercion(CoercionInputShape.Float, CoercionAction.Fail).setCoercion(CoercionInputShape.Boolean, CoercionAction.Fail);
        });
    }
}
