import { ChatContext, ChatContextProvider } from '@/app/chat-context';
import SideBar from '@/components/layout/side-bar';
import FloatHelper from '@/new-components/layout/FloatHelper';
import { GATEWAY_AUTH_CHANGE_EVENT, getGatewayUserInfo, isGatewayAuthenticated, loginWithGateway } from '@/utils/auth';
import { STORAGE_LANG_KEY, STORAGE_USERINFO_KEY, STORAGE_USERINFO_VALID_TIME_KEY } from '@/utils/constants/index';
import { App, Button, ConfigProvider, Form, Input, MappingAlgorithm, message, theme } from 'antd';
import enUS from 'antd/locale/en_US';
import zhCN from 'antd/locale/zh_CN';
import classNames from 'classnames';
import type { AppProps } from 'next/app';
import Head from 'next/head';
import { useRouter } from 'next/router';
import React, { useContext, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import '../app/i18n';
import '../nprogress.css';
import '../styles/globals.css';
// import TopProgressBar from '@/components/layout/top-progress-bar';

const antdDarkTheme: MappingAlgorithm = (seedToken, mapToken) => {
  return {
    ...theme.darkAlgorithm(seedToken, mapToken),
    colorBgBase: '#232734',
    colorBorder: '#828282',
    colorBgContainer: '#232734',
  };
};

function CssWrapper({ children }: { children: React.ReactElement }) {
  const { mode } = useContext(ChatContext);
  const { i18n } = useTranslation();

  useEffect(() => {
    if (mode) {
      document.body?.classList?.add(mode);
      if (mode === 'light') {
        document.body?.classList?.remove('dark');
      } else {
        document.body?.classList?.remove('light');
      }
    }
  }, [mode]);

  useEffect(() => {
    i18n.changeLanguage?.(window.localStorage.getItem(STORAGE_LANG_KEY) || 'zh');
  }, [i18n]);

  return (
    <div>
      {/* <TopProgressBar /> */}
      {children}
    </div>
  );
}

function LayoutWrapper({ children }: { children: React.ReactNode }) {
  const { isMenuExpand, mode } = useContext(ChatContext);
  const { i18n } = useTranslation();
  const [isLogin, setIsLogin] = useState(false);
  const [authChecked, setAuthChecked] = useState(false);
  const [loginLoading, setLoginLoading] = useState(false);

  const router = useRouter();

  // 登录检测
  const handleAuth = () => {
    const userInfo = getGatewayUserInfo();
    const authenticated = isGatewayAuthenticated();
    setIsLogin(authenticated);
    setAuthChecked(true);
    if (authenticated && userInfo) {
      localStorage.setItem(
        STORAGE_USERINFO_KEY,
        JSON.stringify({
          user_id: userInfo.userId,
          user_channel: 'gateway',
          user_no: userInfo.userId,
          nick_name: userInfo.name || userInfo.loginName,
        }),
      );
      localStorage.setItem(STORAGE_USERINFO_VALID_TIME_KEY, Date.now().toString());
    }
  };

  const handleLogin = async (values: { username: string; password: string }) => {
    setLoginLoading(true);
    try {
      await loginWithGateway(values.username, values.password);
      handleAuth();
      message.success('登录成功');
    } catch (error: any) {
      message.error(error?.message || '登录失败');
    } finally {
      setLoginLoading(false);
    }
  };

  useEffect(() => {
    handleAuth();
    window.addEventListener(GATEWAY_AUTH_CHANGE_EVENT, handleAuth);
    return () => window.removeEventListener(GATEWAY_AUTH_CHANGE_EVENT, handleAuth);
  }, []);

  if (!authChecked && !router.pathname.startsWith('/share')) {
    return null;
  }

  const renderLogin = () => (
    <div className='min-h-screen w-screen bg-[#f7f7f9] dark:bg-[#0f1012] flex items-center justify-center px-6'>
      <div className='w-full max-w-[420px] rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-[#15161b] shadow-xl p-7'>
        <div className='mb-6'>
          <div className='text-xs uppercase tracking-[0.22em] text-gray-400 mb-2'>Gateway Login</div>
          <h1 className='text-2xl font-semibold text-gray-900 dark:text-gray-100'>DB-GPT</h1>
          <p className='text-sm text-gray-500 dark:text-gray-400 mt-2'>
            使用网关认证后访问 DB-GPT，后续请求会自动携带 Authorization、X-User-Id 和 X-User-Info。
          </p>
        </div>
        <Form
          layout='vertical'
          initialValues={{ username: 'admin', password: 'Admin@123' }}
          onFinish={handleLogin}
          requiredMark={false}
        >
          <Form.Item name='username' label='Username' rules={[{ required: true, message: '请输入用户名' }]}>
            <Input autoComplete='username' />
          </Form.Item>
          <Form.Item name='password' label='Password' rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password autoComplete='current-password' />
          </Form.Item>
          <Button type='primary' htmlType='submit' loading={loginLoading} block className='h-10'>
            登录
          </Button>
        </Form>
      </div>
    </div>
  );

  const renderContent = (page: React.ReactNode) => {
    if (!isLogin && !router.pathname.startsWith('/share')) {
      return renderLogin();
    }
    if (router.pathname.includes('mobile') || router.pathname.startsWith('/share')) {
      return <>{page}</>;
    }
    return (
      <div className='flex w-screen h-screen overflow-hidden'>
        <Head>
          <meta name='viewport' content='initial-scale=1.0, width=device-width, maximum-scale=1' />
        </Head>
        {router.pathname !== '/construct/app/extra' && (
          <div className={classNames('transition-[width]', isMenuExpand ? 'w-60' : 'w-20', 'hidden', 'md:block')}>
            <SideBar />
          </div>
        )}
        <div className='flex flex-col flex-1 relative overflow-hidden'>{page}</div>
        <FloatHelper />
      </div>
    );
  };

  const pageContent = !isLogin && !router.pathname.startsWith('/share') ? null : children;

  return (
    <ConfigProvider
      locale={i18n.language === 'en' ? enUS : zhCN}
      theme={{
        token: {
          colorPrimary: '#0C75FC',
          borderRadius: 4,
        },
        algorithm: mode === 'dark' ? antdDarkTheme : undefined,
      }}
    >
      <App>{renderContent(pageContent)}</App>
    </ConfigProvider>
  );
}

function MyApp({ Component, pageProps }: AppProps) {
  return (
    <ChatContextProvider>
      <CssWrapper>
        <LayoutWrapper>
          <Component {...pageProps} />
        </LayoutWrapper>
      </CssWrapper>
    </ChatContextProvider>
  );
}

export default MyApp;
