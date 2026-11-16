#import <Foundation/Foundation.h>

@interface SMAppService : NSObject
+ (instancetype)mainAppService;
+ (instancetype)loginItemServiceWithIdentifier:(NSString *)identifier;
- (BOOL)registerAndReturnError:(NSError **)error;
- (BOOL)unregisterAndReturnError:(NSError **)error;
- (NSInteger)status;
@end

@implementation SMAppService
+ (instancetype)mainAppService { return [[self alloc] init]; }
+ (instancetype)loginItemServiceWithIdentifier:(NSString *)identifier { return [[self alloc] init]; }
- (BOOL)registerAndReturnError:(NSError **)error { if (error) *error = nil; return NO; }
- (BOOL)unregisterAndReturnError:(NSError **)error { if (error) *error = nil; return NO; }
- (NSInteger)status { return 0; }
@end
