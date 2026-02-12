import { Link as RouterLink, type LinkProps } from 'react-router-dom'
import { forwardRef } from 'react'
import * as Headless from '@headlessui/react'

export const RadiantLink = forwardRef<HTMLAnchorElement, LinkProps>(
  function RadiantLink(props, ref) {
    return (
      <Headless.DataInteractive>
        <RouterLink ref={ref} {...props} />
      </Headless.DataInteractive>
    )
  }
)
