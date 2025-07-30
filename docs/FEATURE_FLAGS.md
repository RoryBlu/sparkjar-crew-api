# Feature Flag System Documentation

## Overview

The SparkJAR platform includes a comprehensive feature flag system that enables gradual rollout of remote crew execution. This system allows for safe migration from local crew execution to distributed crew services with instant rollback capabilities.

## Key Features

- **Per-Crew Control**: Enable remote execution for specific crews while others remain local
- **Global Flags**: Control behavior across all crews with a single flag
- **Environment Configuration**: Set flags via environment variables for different deployments
- **Runtime Updates**: Change flags without restarting services via admin API
- **Metrics Tracking**: Monitor flag usage and execution patterns
- **Fallback Support**: Automatically fall back to local execution if remote fails

## Architecture

```
┌─────────────────┐       ┌──────────────────┐
│   Job Service   │       │  Feature Flags   │
│                 │──────▶│                  │
│ execute_job()   │       │ is_enabled()     │
└────────┬────────┘       └──────────────────┘
         │                         │
         ▼                         ▼
   Check Flag               Return Decision
         │                         │
         ├─── Remote? ─────────────┤
         │                         │
         ▼                         ▼
┌─────────────────┐       ┌──────────────────┐
│  Crew Client    │       │ Local Execution  │
│ (Remote HTTP)   │       │ (CREW_REGISTRY)  │
└─────────────────┘       └──────────────────┘
```

## Configuration

### Environment Variables

Feature flags can be configured through environment variables in two ways:

1. **Individual Flags**: `FEATURE_FLAG_<FLAG_NAME>=true/false`
   ```bash
   export FEATURE_FLAG_USE_REMOTE_CREWS=true
   export FEATURE_FLAG_USE_REMOTE_CREWS_MEMORY_MAKER_CREW=true
   ```

2. **JSON Configuration**: `FEATURE_FLAGS='{"flag_name": true, ...}'`
   ```bash
   export FEATURE_FLAGS='{
     "use_remote_crews": false,
     "use_remote_crews_memory_maker_crew": true,
     "enable_remote_crew_fallback": true
   }'
   ```

### Default Flags

The system initializes with these default flags:

| Flag Name | Default | Description |
|-----------|---------|-------------|
| `use_remote_crews` | `false` | Route all crew executions to remote service |
| `use_remote_crews_<crew_name>` | `false` | Route specific crew to remote service |
| `enable_crew_metrics` | `true` | Enable detailed metrics for crew execution |
| `enable_remote_crew_fallback` | `false` | Fall back to local if remote fails |

## Usage

### In Job Service

The job service automatically checks feature flags when executing crews:

```python
# In job_service.py
feature_flags = get_feature_flags()
crew_name = job.job_key

if feature_flags.should_use_remote_crew(crew_name):
    # Execute via HTTP to crews service
    result = await crew_client.execute_crew(crew_name, inputs)
else:
    # Execute locally using CREW_REGISTRY
    handler = CREW_REGISTRY[crew_name]()
    result = await handler.execute(inputs)
```

### Admin API Endpoints

#### Get All Feature Flags
```bash
GET /admin/feature-flags
Authorization: Bearer <admin_token>

Response:
{
  "flags": {
    "use_remote_crews": {
      "enabled": false,
      "description": "Route all crew executions to remote service",
      "created_at": "2025-01-07T12:00:00Z",
      "updated_at": "2025-01-07T12:00:00Z"
    }
  },
  "metrics": {
    "total_flags": 6,
    "enabled_flags": 2,
    "total_checks": 150,
    "flag_checks": {
      "use_remote_crews:memory_maker_crew": 50
    }
  }
}
```

#### Update Feature Flag
```bash
POST /admin/feature-flags
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "flag_name": "use_remote_crews_memory_maker_crew",
  "enabled": true,
  "description": "Enable remote execution for memory maker crew"
}
```

#### Reset Metrics
```bash
POST /admin/feature-flags/reset-metrics
Authorization: Bearer <admin_token>
```

## Migration Strategy

### Phase 1: Pilot Crew
1. Deploy crews service with memory_maker_crew
2. Enable flag: `use_remote_crews_memory_maker_crew=true`
3. Monitor for 24 hours
4. Check metrics and error rates

### Phase 2: Gradual Rollout
1. For each additional crew:
   - Enable crew-specific flag
   - Monitor performance
   - Verify results match local execution
   - Leave enabled for observation period

### Phase 3: Full Migration
1. Enable global flag: `use_remote_crews=true`
2. Remove crew-specific flags (global takes precedence)
3. Monitor all crews
4. Disable local crew code after verification period

### Rollback Procedure
If issues occur:
1. Disable affected flag immediately via admin API
2. All new requests will use local execution
3. No service restart required
4. Investigate issues while traffic is safe

## Monitoring

### Key Metrics to Track

1. **Execution Type Distribution**
   - Percentage of remote vs local executions
   - Per-crew breakdown

2. **Performance Comparison**
   - Execution time: remote vs local
   - Success rates by execution type
   - Fallback frequency

3. **Error Patterns**
   - Remote execution failures
   - Fallback success rate
   - Error types and frequencies

### Logging

All flag decisions are logged:
```
INFO: Feature flag 'use_remote_crews_memory_maker_crew' is enabled
INFO: Using remote execution for crew: memory_maker_crew
INFO: Job 123 completed successfully via remote execution
```

### Database Events

Job events track execution type:
```json
{
  "event_type": "job_completed",
  "event_data": {
    "message": "Job completed successfully via remote crew execution",
    "execution_type": "remote",
    "crew_name": "memory_maker_crew",
    "execution_time": 5.2,
    "total_time": 6.1
  }
}
```

## Best Practices

1. **Test in Staging First**
   - Enable flags in staging environment
   - Run comprehensive tests
   - Verify metrics collection

2. **Monitor After Changes**
   - Watch error rates for 1 hour after enabling
   - Check performance metrics
   - Review logs for anomalies

3. **Use Specific Flags First**
   - Enable per-crew flags before global
   - Test each crew independently
   - Build confidence gradually

4. **Document Changes**
   - Log who changed flags and when
   - Document reason for changes
   - Track in deployment notes

5. **Plan for Failure**
   - Know how to disable flags quickly
   - Have monitoring alerts set up
   - Keep fallback option available initially

## Troubleshooting

### Flag Not Taking Effect
1. Check flag name spelling (case-sensitive)
2. Verify token has admin scope
3. Check metrics to see if flag is being evaluated
4. Review logs for flag decision output

### Remote Execution Failing
1. Check crews service health: `GET /health`
2. Verify network connectivity
3. Check authentication tokens
4. Review crew service logs
5. Enable fallback temporarily

### Performance Degradation
1. Compare metrics before/after flag change
2. Check network latency to crews service
3. Review crew service resource usage
4. Consider connection pool settings

## Security Considerations

- Admin scope required for flag management
- All flag changes are logged with user ID
- No sensitive data in flag names or descriptions
- Flags don't affect authentication/authorization

## Future Enhancements

1. **A/B Testing**: Route percentage of traffic to remote
2. **Automated Rollout**: Gradually increase remote percentage
3. **Performance Triggers**: Auto-disable if latency exceeds threshold
4. **Flag Inheritance**: Crew categories with shared flags
5. **Audit Trail**: Complete history of flag changes