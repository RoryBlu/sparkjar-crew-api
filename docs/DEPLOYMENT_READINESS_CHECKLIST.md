# Crew-API Deployment Readiness Checklist

## Prerequisites ❌ NOT READY

### Dependencies
- [ ] Set up dedicated virtual environment using `./setup_venv.sh`
- [ ] Install crewai==0.134.0 (latest stable)
- [ ] Install minimal requirements to avoid conflicts
- [ ] Test imports work correctly
- [ ] Document any dependency issues in requirements-minimal.txt

### Configuration
- [ ] Update DATABASE_URL references to use DIRECT/POOLED pattern
- [ ] Verify all required environment variables are documented
- [ ] Test configuration validation logic

### Database
- [x] Database models updated (metadata → metadata_json)
- [ ] Verify crew-api works with updated shared models
- [ ] Test database connections (both DIRECT and POOLED)
- [ ] Run any necessary migrations

### Tests
- [ ] Fix config validation tests
- [ ] Install missing test dependencies
- [ ] Fix import path issues in tests
- [ ] All tests passing (currently 3/15 passing)

### API Endpoints
- [ ] Verify all API endpoints work with updated models
- [ ] Test job creation and execution
- [ ] Test crew handler functionality
- [ ] Verify MCP integration works

### Documentation
- [x] API documentation exists
- [ ] Update for any breaking changes
- [ ] Document new environment variables
- [ ] Update deployment guide

## Blocking Issues

1. **Missing crewai Package**
   - Critical dependency not installed
   - Blocks most functionality tests

2. **Outdated Tests**
   - Config tests need updates
   - Import paths need fixing

3. **Unknown Impact of Model Changes**
   - metadata → metadata_json change needs testing
   - May affect crew job storage/retrieval

## Recommended Actions

1. **DO NOT DEPLOY** until dependencies are installed
2. Install all requirements and test basic functionality
3. Update and run all tests
4. Perform integration testing with memory service
5. Update deployment documentation

## Deployment Steps (When Ready)

1. Install all dependencies
2. Set environment variables:
   - OPENAI_API_KEY
   - DATABASE_URL_DIRECT
   - DATABASE_URL_POOLED
   - SUPABASE_URL
   - SUPABASE_SECRET_KEY
   - API_SECRET_KEY
   - Other service URLs

3. Run database migrations if needed
4. Start service with proper port configuration
5. Verify health endpoints
6. Test core functionality